"""The Version view: everything a Journalist sees about an embed's Versions, and the publish gate.

Each Version comes with its signed preview URL, whether it is published, its pinned
Snippet and Embed URL once it is, and its Quality check findings. The check always runs
on the document with the dataset contents removed (ADR 0002): a dataset's cells are
data, not code, so they never produce findings.
"""

from dataclasses import dataclass
from typing import Literal, Self

from pydantic import BaseModel

from embeds.datasets import without_dataset_contents
from embeds.delivery import embed_url, snippet
from embeds.previews import Previews
from embeds.quality_check import Finding, Severity, check, has_blockers
from embeds.store import Store, Version


class Delivery(BaseModel):
    """What the journalist pastes into an article."""

    snippet: str
    embed_url: str


class FindingOut(BaseModel):
    rule: str
    severity: Severity
    detail: str

    @classmethod
    def of(cls, finding: Finding) -> Self:
        return cls(rule=finding.rule, severity=finding.severity, detail=finding.detail)


class VersionOut(BaseModel):
    number: int
    created_at: str
    preview_url: str
    published: bool
    delivery: Delivery | None  # Pinned to this version; only once it is published.
    findings: list[FindingOut]  # From the quality check.


@dataclass(frozen=True)
class EmbedVersions:
    versions: list[VersionOut]
    delivery: Delivery | None  # Follows the newest published version; once one exists.


@dataclass(frozen=True)
class Publishing:
    """`blocked` and `unconfirmed_warnings` come with the findings that stopped it."""

    outcome: Literal["published", "no_such_version", "blocked", "unconfirmed_warnings"]
    findings: list[FindingOut]


class VersionView:
    def __init__(self, store: Store, previews: Previews, embed_origin: str) -> None:
        self._store = store
        self._previews = previews
        self._origin = embed_origin

    def of(self, version: Version) -> VersionOut:
        embed_id, number = version.embed_id, version.number
        return VersionOut(
            number=number,
            created_at=version.created_at,
            preview_url=self._previews.url(embed_id, number),
            published=version.published,
            delivery=self._delivery(embed_id, number) if version.published else None,
            findings=[FindingOut.of(f) for f in self._findings(version)],
        )

    def of_embed(self, embed_id: str) -> EmbedVersions:
        versions = [self.of(v) for v in self._store.versions_of(embed_id)]
        published = any(v.published for v in versions)
        return EmbedVersions(versions, self._delivery(embed_id) if published else None)

    def publish(self, embed_id: str, number: int, accept_warnings: bool) -> Publishing:
        """Blockers refuse; warnings need the journalist to confirm them."""
        version = self._store.version(embed_id, number)
        if version is None:
            return Publishing("no_such_version", [])
        findings = self._findings(version)
        refused = [FindingOut.of(f) for f in findings]
        if has_blockers(findings):
            return Publishing("blocked", refused)
        if findings and not accept_warnings:
            return Publishing("unconfirmed_warnings", refused)
        self._store.publish(embed_id, number)
        return Publishing("published", [])

    def _findings(self, version: Version) -> list[Finding]:
        return check(without_dataset_contents(version.html), self._origin)

    def _delivery(self, embed_id: str, number: int | None = None) -> Delivery:
        return Delivery(
            snippet=snippet(self._origin, embed_id, number),
            embed_url=embed_url(self._origin, embed_id, number),
        )

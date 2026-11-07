import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { OpenedEmbed, Version } from "./api";

interface Props {
  embed: OpenedEmbed;
  shown: Version | null;
}

/** What the journalist pastes into an article, once something is published. */
export function PublishPanel({ embed, shown }: Props) {
  const { t } = useTranslation();
  if (!embed.delivery) {
    return <p className="hint publish-panel">{t("publish.notYet")}</p>;
  }

  const pinned = shown?.delivery ? { number: shown.number, ...shown.delivery } : null;
  return (
    <div className="publish-panel">
      <h3>{t("publish.heading")}</h3>
      <CopyField label={t("publish.snippetLatest")} value={embed.delivery.snippet} />
      <CopyField label={t("publish.urlLatest")} value={embed.delivery.embed_url} />
      <TestArticleLink embedId={embed.id} label={t("publish.testArticle")} />
      {pinned && (
        <>
          <CopyField label={t("publish.snippetPinned", { number: pinned.number })} value={pinned.snippet} />
          <CopyField label={t("publish.urlPinned", { number: pinned.number })} value={pinned.embed_url} />
          <TestArticleLink
            embedId={embed.id}
            version={pinned.number}
            label={t("publish.testArticlePinned", { number: pinned.number })}
          />
        </>
      )}
    </div>
  );
}

function TestArticleLink({ embedId, version, label }: { embedId: string; version?: number; label: string }) {
  const query = new URLSearchParams({ embed: embedId, ...(version ? { version: String(version) } : {}) });
  return (
    <a href={`/test-article?${query}`} target="_blank" rel="noopener">
      {label}
    </a>
  );
}

function CopyField({ label, value }: { label: string; value: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard blocked: the field is selectable, so the journalist can copy by hand.
    }
  }

  return (
    <label className="copy-field">
      <span>{label}</span>
      <span className="row">
        <input readOnly value={value} onFocus={(e) => e.target.select()} />
        <button type="button" onClick={copy}>
          {copied ? t("publish.copied") : t("publish.copy")}
        </button>
      </span>
    </label>
  );
}

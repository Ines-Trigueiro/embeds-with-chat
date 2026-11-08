import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type OpenedEmbed, type Version } from "./api";
import { bySeverity, Findings } from "./Findings";
import { Icon, type IconName } from "./Icon";
import { Modal } from "./Modal";

interface Props {
  journalist: string;
  embed: OpenedEmbed;
  /** The version on screen: the one to publish, and the one "pinned" code refers to. */
  version: Version;
  onClose: () => void;
  onPublished: (updated: OpenedEmbed) => void;
}

/**
 * Publishing, then getting the embed into an article, for journalists who aren't developers:
 * the quality check first, then one button that copies the code and three plain steps.
 */
export function PublishDialog({ journalist, embed, version, onClose, onPublished }: Props) {
  const { t } = useTranslation();
  const [accepted, setAccepted] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justPublished, setJustPublished] = useState(false);

  const { blockers, warnings } = bySeverity(version.findings);
  const canPublish = blockers.length === 0 && (warnings.length === 0 || accepted);
  const status = blockers.length > 0 ? "block" : warnings.length > 0 ? "warn" : "ok";

  async function publish() {
    setPublishing(true);
    setError(null);
    try {
      onPublished(await api.publish(journalist, embed.id, version.number, warnings.length > 0));
      setJustPublished(true);
      requestAnimationFrame(() => document.querySelector<HTMLElement>("dialog .copy-snippet")?.focus());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPublishing(false);
    }
  }

  const showCode = version.published || justPublished;
  return (
    <Modal
      title={showCode ? t("publish.codeTitle") : t("publish.dialogTitle", { number: version.number })}
      closeLabel={t("publish.close")}
      onClose={onClose}
    >
      {showCode && embed.delivery ? (
        <ArticleSteps embed={embed} version={version} justPublished={justPublished} />
      ) : (
        <>
          <p className={`callout ${status}`}>
            <Icon name={STATUS[status].icon} /> {t(STATUS[status].text)}
          </p>
          {version.findings.length > 0 && <Findings findings={version.findings} />}
          {status === "warn" && (
            <label className="checkbox">
              <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
              {t("publish.acceptWarnings")}
            </label>
          )}
          {error && <p className="error">{error}</p>}
          <div className="dialog-actions">
            <button onClick={onClose}>{t("publish.cancel")}</button>
            <button className="primary" disabled={!canPublish || publishing} onClick={publish}>
              <Icon name="publish" />
              {publishing ? t("publish.publishing") : t("publish.confirm")}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

const STATUS = {
  block: { icon: "blocker", text: "publish.blocked" },
  warn: { icon: "warning", text: "publish.warnings" },
  ok: { icon: "check", text: "publish.ready" },
} as const;

function ArticleSteps({ embed, version, justPublished }: { embed: OpenedEmbed; version: Version; justPublished: boolean }) {
  const { t } = useTranslation();
  const delivery = embed.delivery!;
  const steps: [IconName, string][] = [
    ["copy", t("publish.step1")],
    ["code", t("publish.step2")],
    ["eye", t("publish.step3")],
  ];
  const testArticle = `/test-article?${new URLSearchParams({ embed: embed.id })}`;

  return (
    <>
      {justPublished && (
        <p className="callout ok">
          <Icon name="check" /> {t("publish.justPublished", { number: version.number })}
        </p>
      )}
      <CopySnippetButton value={delivery.snippet} />
      <ol className="steps">
        {steps.map(([icon, text], i) => (
          <li key={i}>
            <span className="step-icon" aria-hidden="true">
              <Icon name={icon} size={16} />
            </span>
            <span>
              <strong>{i + 1}.</strong> {text}
            </span>
          </li>
        ))}
      </ol>
      <p className="callout info">
        <Icon name="info" /> {t("publish.updates")}
      </p>
      <a className="test-article" href={testArticle} target="_blank" rel="noopener">
        <Icon name="external" size={16} />
        {t("publish.testArticle")}
      </a>
      <details className="advanced">
        <summary>{t("publish.advanced")}</summary>
        <div className="advanced-body">
          {version.delivery ? (
            <>
              <p className="hint">{t("publish.pinnedHint", { number: version.number })}</p>
              <CopyField label={t("publish.pinnedSnippet", { number: version.number })} value={version.delivery.snippet} />
              <CopyField label={t("publish.urlPinned", { number: version.number })} value={version.delivery.embed_url} />
            </>
          ) : (
            <p className="hint">{t("publish.notPublishedPinned")}</p>
          )}
          <CopyField label={t("publish.urlLatest")} value={delivery.embed_url} />
        </div>
      </details>
    </>
  );
}

function useCopy(value: string): [boolean, () => void] {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the code is selectable under Advanced, so it can be copied by hand.
    }
  }
  return [copied, copy];
}

function CopySnippetButton({ value }: { value: string }) {
  const { t } = useTranslation();
  const [copied, copy] = useCopy(value);
  return (
    <button className={`primary big copy-snippet${copied ? " copied" : ""}`} onClick={copy}>
      <Icon name={copied ? "check" : "copy"} />
      {copied ? t("publish.copied") : t("publish.copySnippet")}
    </button>
  );
}

function CopyField({ label, value }: { label: string; value: string }) {
  const { t } = useTranslation();
  const [copied, copy] = useCopy(value);
  return (
    <label className="copy-field">
      <span>{label}</span>
      <span className="copy-row">
        <input readOnly value={value} onFocus={(e) => e.target.select()} />
        <button
          type="button"
          className="icon-only"
          title={copied ? t("publish.copied") : t("publish.copy")}
          aria-label={copied ? t("publish.copied") : t("publish.copy")}
          onClick={copy}
        >
          <Icon name={copied ? "check" : "copy"} size={16} />
        </button>
      </span>
    </label>
  );
}

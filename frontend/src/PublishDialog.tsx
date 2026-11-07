import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type OpenedEmbed, type Version } from "./api";
import { Findings } from "./Findings";
import { Icon, type IconName } from "./Icon";

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
  const dialog = useRef<HTMLDialogElement>(null);
  const [accepted, setAccepted] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justPublished, setJustPublished] = useState(false);

  useEffect(() => {
    // Modal: focus stays inside, and Escape closes it. Unmounting removes it, so no cleanup.
    const element = dialog.current;
    if (!element || element.open) return;
    element.showModal();
    // Start on the main action, not on the close button the browser would pick.
    element.querySelector<HTMLElement>(".copy-snippet, .dialog-actions .primary:enabled")?.focus();
  }, []);

  const blockers = version.findings.filter((f) => f.severity === "block");
  const warnings = version.findings.filter((f) => f.severity === "warn");
  const canPublish = blockers.length === 0 && (warnings.length === 0 || accepted);

  async function publish() {
    setPublishing(true);
    setError(null);
    try {
      onPublished(await api.publish(journalist, embed.id, version.number, warnings.length > 0));
      setJustPublished(true);
      requestAnimationFrame(() => dialog.current?.querySelector<HTMLElement>(".copy-snippet")?.focus());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPublishing(false);
    }
  }

  const showCode = version.published || justPublished;
  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby="publish-title"
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && dialog.current.close()} // A click on the backdrop.
    >
      <div className="dialog-head">
        <h2 id="publish-title">
          {showCode ? t("publish.codeTitle") : t("publish.dialogTitle", { number: version.number })}
        </h2>
        <button
          className="ghost icon-only"
          title={t("publish.close")}
          aria-label={t("publish.close")}
          onClick={() => dialog.current?.close()}
        >
          <Icon name="close" />
        </button>
      </div>

      {showCode && embed.delivery ? (
        <ArticleSteps embed={embed} version={version} justPublished={justPublished} />
      ) : (
        <div className="dialog-body">
          {blockers.length > 0 ? (
            <p className="callout block">
              <Icon name="blocker" /> {t("publish.blocked")}
            </p>
          ) : warnings.length > 0 ? (
            <p className="callout warn">
              <Icon name="warning" /> {t("publish.warnings")}
            </p>
          ) : (
            <p className="callout ok">
              <Icon name="check" /> {t("publish.ready")}
            </p>
          )}
          {version.findings.length > 0 && <Findings findings={version.findings} />}
          {blockers.length === 0 && warnings.length > 0 && (
            <label className="checkbox">
              <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
              {t("publish.acceptWarnings")}
            </label>
          )}
          {error && <p className="error">{error}</p>}
          <div className="dialog-actions">
            <button onClick={() => dialog.current?.close()}>{t("publish.cancel")}</button>
            <button className="primary" disabled={!canPublish || publishing} onClick={publish}>
              <Icon name="publish" />
              {publishing ? t("publish.publishing") : t("publish.confirm")}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}

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
    <div className="dialog-body">
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
    </div>
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

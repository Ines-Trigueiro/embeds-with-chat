import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";

import { ChatMarkdown } from "./ChatMarkdown";
import { api, type Embed } from "./api";
import { EditableTitle } from "./EditableTitle";
import { ConfirmDialog } from "./ConfirmDialog";
import { Flag } from "./Flag";
import { bySeverity, FindingChips } from "./Findings";
import { currentLanguage, type Language } from "./i18n";
import { Icon } from "./Icon";
import { LanguageSelect } from "./LanguagePicker";
import { Preview, type Device } from "./Preview";
import { PublishDialog } from "./PublishDialog";
import { Workspace, type MessageTurn, type TranslationMarker as Marker } from "./Workspace";

interface Props {
  journalist: string;
  /**
   * The embed to open, read once: null for a new embed, which is created when the journalist
   * first sends or attaches something. The editor then keeps working on it (no reload).
   */
  embedId: string | null;
  /** The Title as the sidebar knows it, so a rename there shows here too. */
  title: string | null;
  onOpenSidebar: () => void;
  onCreated: (embed: Embed) => void;
  onChanged: (changes: Pick<Embed, "id"> & Partial<Embed>) => void;
  onRename: (title: string) => void;
}

export function EmbedEditor({ journalist, embedId, title, onOpenSidebar, onCreated, onChanged, onRename }: Props) {
  const { t } = useTranslation();
  // App remounts the editor per navigation, so one Workspace per mount is one per embed.
  const [workspace] = useState(
    () => new Workspace(api, journalist, currentLanguage(), { created: onCreated, changed: onChanged }),
  );
  const { embed, newEmbedLanguage, loadError, turns, shownNumber, progressHtml, streaming, attaching, attachError } =
    useSyncExternalStore(workspace.subscribe, workspace.getState);
  const [input, setInput] = useState("");
  const [device, setDevice] = useState<Device>("mobile");
  const [pane, setPane] = useState<"chat" | "preview">("chat"); // Phones show one at a time.
  const [publishing, setPublishing] = useState(false); // The publish dialog is open.
  const [translating, setTranslating] = useState<Language | null>(null); // Asking to translate.
  const fileInput = useRef<HTMLInputElement>(null);
  const turnList = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (embedId !== null) workspace.open(embedId);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- App remounts the editor per navigation.

  useEffect(() => {
    // Scroll only the conversation, never the page around it.
    const list = turnList.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [turns]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    await workspace.send(content, currentLanguage());
  }

  async function attach(file: File) {
    await workspace.attach(file);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function changeEmbedLanguage(language: Language) {
    if ((await workspace.changeEmbedLanguage(language)) === "needs-translation") setTranslating(language);
  }

  const showVersion = (number: number) => workspace.show(number);

  if (loadError) return <p className="error page-message">{loadError}</p>;
  if (embedId !== null && !embed) return <p className="hint page-message">{t("sidebar.loading")}</p>;

  const versions = embed?.versions ?? [];
  const version = versions.find((v) => v.number === shownNumber) ?? null;
  const blocked = bySeverity(version?.findings ?? []).blockers.length > 0;
  const latestNumber = versions.at(-1)?.number ?? null;
  const shownTitle = title ?? embed?.title ?? null;

  return (
    <div className={`editor show-${pane}`}>
      <div className="mobile-bar">
        <button
          className="ghost icon-only"
          title={t("sidebar.open")}
          aria-label={t("sidebar.open")}
          onClick={onOpenSidebar}
        >
          <Icon name="menu" />
        </button>
        <div className="pane-switch" role="tablist" aria-label={t("editor.panes")}>
          {(["chat", "preview"] as const).map((p) => (
            <button
              key={p}
              role="tab"
              aria-selected={pane === p}
              className={pane === p ? "on" : ""}
              onClick={() => setPane(p)}
            >
              <Icon name={p === "chat" ? "chat" : "eye"} size={16} />
              {t(`editor.pane.${p}`)}
            </button>
          ))}
        </div>
      </div>

      <section className="chat card">
        <div className="chat-head">
          {embed ? (
            <EditableTitle title={shownTitle} onRename={onRename} />
          ) : (
            <h2 className="untitled">{t("sidebar.new")}</h2>
          )}
          <span className="embed-language" title={t("editor.embedLanguageHint")}>
            <LanguageSelect
              value={embed?.embed_language ?? newEmbedLanguage}
              onChange={changeEmbedLanguage}
              label={t("editor.embedLanguage")}
              disabled={streaming}
            />
          </span>
        </div>
        <ol className="turns" ref={turnList}>
          {turns.length === 0 && (
            <li className="empty-chat">
              <span className="logo" aria-hidden="true">
                <Icon name="sparkle" size={24} />
              </span>
              <h3>{t("editor.emptyHeading")}</h3>
              <div className="suggestions">
                {(["quiz", "calculator", "chart", "map"] as const).map((kind) => (
                  <button key={kind} type="button" onClick={() => setInput(t(`editor.suggestions.${kind}`))}>
                    {t(`editor.suggestions.${kind}`)}
                  </button>
                ))}
              </div>
            </li>
          )}
          {turns.map((turn, i) =>
            turn.kind === "translation" ? (
              <TranslationMarker key={i} marker={turn} onShow={showVersion} />
            ) : (
              <TurnItem key={i} turn={turn} writing={progressHtml !== null} onShow={showVersion} />
            ),
          )}
        </ol>
        {embed && embed.attachments.length > 0 && (
          <ul className="attachments" aria-label={t("attachments.heading")}>
            {embed.attachments.map((a) => (
              <li key={a.id} title={a.columns?.map((c) => c.name).join(", ")}>
                <Icon name={a.kind === "dataset" ? "table" : "image"} size={14} /> {a.name}
                {a.rows !== null && <span className="hint"> · {t("attachments.rows", { count: a.rows })}</span>}
              </li>
            ))}
          </ul>
        )}
        {attachError && <p className="error">{attachError}</p>}
        <form className="composer" onSubmit={send}>
          <input
            ref={fileInput}
            type="file"
            hidden
            accept=".csv,.xlsx,image/png,image/jpeg,image/gif,image/webp"
            onChange={(e) => e.target.files?.[0] && attach(e.target.files[0])}
          />
          <button
            type="button"
            className="ghost icon-only attach"
            title={t("attachments.attach")}
            aria-label={t("attachments.attach")}
            disabled={attaching || streaming}
            onClick={() => fileInput.current?.click()}
          >
            <Icon name="attach" />
          </button>
          <textarea
            value={input}
            rows={2}
            placeholder={t("editor.placeholder")}
            aria-label={t("editor.placeholder")}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) send(e);
            }}
          />
          <button
            type="submit"
            className="primary icon-only send"
            title={t("editor.send")}
            aria-label={t("editor.send")}
            disabled={streaming || !input.trim()}
          >
            <Icon name="send" />
          </button>
        </form>
      </section>

      <section className="preview card">
        <div className="preview-bar">
          {versions.length === 0 ? (
            <span>{t("editor.noVersion")}</span>
          ) : (
            <label className="version-picker">
              <select
                aria-label={t("editor.showing")}
                value={shownNumber ?? ""}
                disabled={streaming}
                onChange={(e) => showVersion(Number(e.target.value))}
              >
                {[...versions].reverse().map((v) => (
                  <option key={v.number} value={v.number}>
                    {t("editor.version", { number: v.number })}
                    {v.number === latestNumber ? ` ${t("editor.latest")}` : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          {version && embed && (
            <span className="publish-actions">
              {version.published ? (
                <span className="badge-published">
                  <Icon name="check" size={14} />
                  {t("publish.published")}
                </span>
              ) : (
                <button
                  className="primary"
                  disabled={streaming}
                  title={blocked ? t("quality.cannotPublish") : undefined}
                  onClick={() => setPublishing(true)}
                >
                  <Icon name="publish" size={16} />
                  {t("publish.publish", { number: version.number })}
                </button>
              )}
              {(version.published || embed.delivery) && (
                <button
                  className={version.published ? "primary" : "icon-only"}
                  disabled={streaming}
                  title={t("publish.getSnippet")}
                  aria-label={t("publish.getSnippet")}
                  onClick={() => setPublishing(true)}
                >
                  <Icon name="code" size={16} />
                  {version.published && <span className="wide-only">{t("publish.getSnippet")}</span>}
                </button>
              )}
            </span>
          )}
          <div className="toggle" role="group" aria-label={t("editor.previewSize")}>
            {(["mobile", "desktop"] as const).map((d) => (
              <button
                key={d}
                className={device === d ? "on" : ""}
                aria-pressed={device === d}
                title={t(`editor.${d}`)}
                aria-label={t(`editor.${d}`)}
                onClick={() => setDevice(d)}
              >
                <Icon name={d} size={17} />
              </button>
            ))}
          </div>
        </div>
        {version && !streaming && <FindingChips key={version.number} findings={version.findings} />}
        <Preview
          versionUrl={version?.preview_url ?? null}
          progressFrameUrl={embed?.progress_frame_url ?? ""}
          progressHtml={progressHtml}
          device={device}
        />
      </section>
      {translating && embed && latestNumber !== null && (
        <ConfirmDialog
          title={t("editor.translate.title", { language: t(`languages.${translating}`) })}
          confirm={t("editor.translate.confirm")}
          cancel={t("publish.cancel")}
          onConfirm={() => workspace.translate(translating, currentLanguage())}
          onClose={() => setTranslating(null)}
        >
          <p className="callout info">
            <Flag language={translating} />
            {t("editor.translate.body", {
              language: t(`languages.${translating}`),
              number: latestNumber,
              next: latestNumber + 1,
            })}
          </p>
        </ConfirmDialog>
      )}
      {publishing && embed && version && (
        <PublishDialog
          journalist={journalist}
          embed={embed}
          version={version}
          onClose={() => setPublishing(false)}
          onPublished={(updated) => workspace.published(updated)}
        />
      )}
    </div>
  );
}

const MARKER_TEXT = {
  pending: "editor.translatingTo",
  finished: "editor.translatedTo",
  failed: "editor.notTranslatedTo",
} as const;

/** A Translation in the conversation: the journalist typed nothing, so it's a marker. */
function TranslationMarker({ marker, onShow }: { marker: Marker; onShow: (number: number) => void }) {
  const { language, state, version_number: done } = marker;
  const { t } = useTranslation();
  const pending = state === "pending";
  const text = MARKER_TEXT[state];
  return (
    <li className="turn marker">
      <Flag language={language} />
      <span className={pending ? "pulsing-text" : undefined}>{t(text, { language: t(`languages.${language}`) })}</span>
      {done !== null && <VersionBadge number={done} onShow={onShow} />}
    </li>
  );
}

function TurnItem(props: {
  turn: MessageTurn;
  /** The work in progress is streaming into the preview. */
  writing: boolean;
  onShow: (number: number) => void;
}) {
  const { turn, writing, onShow } = props;
  const { t } = useTranslation();
  const { live } = turn;
  const waiting = live && !turn.text;
  return (
    <li className={`turn ${turn.role}`}>
      {turn.guides.map((guide, g) => (
        <p key={g} className={waiting && g === turn.guides.length - 1 ? "status pulsing" : "status"}>
          {t("editor.readingGuide", { name: t(`guides.${guide}`, { defaultValue: guide }) })}
        </p>
      ))}
      {turn.role === "model" ? <ChatMarkdown text={turn.text} /> : turn.text}
      {waiting && turn.guides.length === 0 && <p className="status pulsing">{t("editor.thinking")}</p>}
      {live && turn.text && writing && <p className="status pulsing">{t("editor.writing")}</p>}
      {turn.version_number !== null && <VersionBadge number={turn.version_number} onShow={onShow} />}
      {turn.error && <p className="error">{turn.error}</p>}
    </li>
  );
}

function VersionBadge({ number, onShow }: { number: number; onShow: (number: number) => void }) {
  const { t } = useTranslation();
  return (
    <button className="badge" onClick={() => onShow(number)}>
      {t("editor.version", { number })}
    </button>
  );
}

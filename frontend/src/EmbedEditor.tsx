import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChatMarkdown } from "./ChatMarkdown";
import { api, type ChatEvent, type Embed, type Message, type OpenedEmbed } from "./api";
import { EditableTitle } from "./EditableTitle";
import { ConfirmDialog } from "./ConfirmDialog";
import { Flag } from "./Flag";
import { bySeverity, FindingChips } from "./Findings";
import { currentLanguage, type Language } from "./i18n";
import { Icon } from "./Icon";
import { LanguageSelect } from "./LanguagePicker";
import { Preview, type Device } from "./Preview";
import { PublishDialog } from "./PublishDialog";

interface Turn extends Message {
  error?: string;
}

const EMPTY_TURN: Turn = { role: "journalist", kind: "message", text: "", version_number: null, guides: [] };

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
  const [embed, setEmbed] = useState<OpenedEmbed | null>(null);
  const [newLanguage, setNewLanguage] = useState<Language>(currentLanguage);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [shownNumber, setShownNumber] = useState<number | null>(null);
  const [progressHtml, setProgressHtml] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [device, setDevice] = useState<Device>("mobile");
  const [pane, setPane] = useState<"chat" | "preview">("chat"); // Phones show one at a time.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false); // The publish dialog is open.
  const [translating, setTranslating] = useState<Language | null>(null); // Asking to translate.
  const [attachError, setAttachError] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const turnList = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (embedId === null) return;
    api.openEmbed(journalist, embedId).then(
      (opened) => {
        setEmbed(opened);
        setTurns(opened.messages);
        setShownNumber(opened.latest_version?.number ?? null);
      },
      (e: Error) => setLoadError(e.message),
    );
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- App remounts the editor per navigation.

  useEffect(() => {
    // Scroll only the conversation, never the page around it.
    const list = turnList.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [turns]);

  /** The embed to work on, creating it first if this is a new one. */
  async function ensureEmbed(): Promise<OpenedEmbed> {
    if (embed) return embed;
    const created = await api.createEmbed(journalist, newLanguage);
    const opened = await api.openEmbed(journalist, created.id);
    setEmbed(opened);
    onCreated(created);
    return opened;
  }

  function updateModelTurn(update: (turn: Turn) => Turn) {
    setTurns((current) => [...current.slice(0, -1), update(current[current.length - 1])]);
  }

  /** Show one model turn as it streams in, after the journalist's (or the tool's) message. */
  async function runTurn(asked: Turn, start: (id: string) => AsyncGenerator<ChatEvent>, onVersion?: () => void) {
    setStreaming(true);
    setTurns((current) => [...current, asked, { ...EMPTY_TURN, role: "model" }]);
    try {
      const { id } = await ensureEmbed();
      for await (const { event, data } of start(id)) {
        if (event === "title") onChanged({ id, title: data.title });
        else if (event === "guide") updateModelTurn((t) => ({ ...t, guides: [...t.guides, data.name] }));
        else if (event === "text") updateModelTurn((t) => ({ ...t, text: t.text + data.delta }));
        else if (event === "progress") setProgressHtml(data.html);
        else if (event === "version") {
          setEmbed((current) => current && { ...current, versions: [...current.versions, data] });
          setShownNumber(data.number);
          updateModelTurn((t) => ({ ...t, version_number: data.number }));
          onVersion?.();
        } else if (event === "error") updateModelTurn((t) => ({ ...t, error: data.message }));
        else if (event === "done") updateModelTurn((t) => ({ ...t, text: data.text }));
      }
    } catch (e) {
      updateModelTurn((t) => ({ ...t, error: (e as Error).message }));
    } finally {
      setProgressHtml(null);
      setStreaming(false);
    }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    await runTurn({ ...EMPTY_TURN, text: content }, (id) =>
      api.sendMessage(journalist, id, content, currentLanguage()),
    );
  }

  /** A Translation (ADR 0004): the embed language only changes once the translated version exists. */
  async function translate(language: Language) {
    await runTurn(
      { ...EMPTY_TURN, kind: "translation", text: language },
      (id) => api.translate(journalist, id, language, currentLanguage()),
      () => setEmbed((current) => current && { ...current, embed_language: language }),
    );
  }

  async function attach(file: File) {
    setAttachError(null);
    setAttaching(true);
    try {
      const { id } = await ensureEmbed();
      const attachment = await api.attach(journalist, id, file);
      setEmbed((current) => current && { ...current, attachments: [...current.attachments, attachment] });
    } catch (e) {
      setAttachError((e as Error).message);
    } finally {
      setAttaching(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function published(updated: OpenedEmbed) {
    setEmbed(updated);
    onChanged({ id: updated.id, published: true });
  }

  async function changeEmbedLanguage(embed_language: Language) {
    if (!embed) {
      setNewLanguage(embed_language);
      return;
    }
    if (versions.length > 0) {
      setTranslating(embed_language); // Ask first: a Translation costs a model call and a version.
      return;
    }
    const changed = await api.changeEmbed(journalist, embed.id, { embed_language });
    setEmbed((current) => current && { ...current, embed_language: changed.embed_language });
  }

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
              value={embed?.embed_language ?? newLanguage}
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
              <TranslationMarker
                key={i}
                language={turn.text as Language}
                pending={streaming && i === turns.length - 2}
                done={turns[i + 1]?.version_number ?? null}
                onShow={setShownNumber}
              />
            ) : (
              <TurnItem
                key={i}
                turn={turn}
                live={streaming && i === turns.length - 1}
                writing={progressHtml !== null}
                onShow={setShownNumber}
              />
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
                onChange={(e) => setShownNumber(Number(e.target.value))}
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
          onConfirm={() => translate(translating)}
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
          onPublished={published}
        />
      )}
    </div>
  );
}

/** A Translation in the conversation: the journalist typed nothing, so it's a marker. */
function TranslationMarker(props: {
  language: Language;
  /** Its reply is arriving right now. */
  pending: boolean;
  /** The version it made, if any. */
  done: number | null;
  onShow: (number: number) => void;
}) {
  const { language, pending, done, onShow } = props;
  const { t } = useTranslation();
  const text = pending ? "editor.translatingTo" : done !== null ? "editor.translatedTo" : "editor.notTranslatedTo";
  return (
    <li className="turn marker">
      <Flag language={language} />
      <span className={pending ? "pulsing-text" : undefined}>{t(text, { language: t(`languages.${language}`) })}</span>
      {done !== null && <VersionBadge number={done} onShow={onShow} />}
    </li>
  );
}

function TurnItem(props: {
  turn: Turn;
  /** The reply arriving right now. */
  live: boolean;
  /** The work in progress is streaming into the preview. */
  writing: boolean;
  onShow: (number: number) => void;
}) {
  const { turn, live, writing, onShow } = props;
  const { t } = useTranslation();
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

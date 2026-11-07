import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChatMarkdown } from "./ChatMarkdown";
import { api, type Embed, type Message, type OpenedEmbed, type Version } from "./api";
import { EditableTitle } from "./EditableTitle";
import { Findings } from "./Findings";
import { currentLanguage, type Language } from "./i18n";
import { Icon } from "./Icon";
import { LanguageSelect } from "./LanguagePicker";
import { Preview, type Device } from "./Preview";
import { PublishPanel } from "./PublishPanel";

interface Turn extends Message {
  error?: string;
}

interface Props {
  journalist: string;
  /** Null for a new embed: it is created when the journalist first sends or attaches something. */
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
  const [versions, setVersions] = useState<Version[]>([]);
  const [shownNumber, setShownNumber] = useState<number | null>(null);
  const [progressHtml, setProgressHtml] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [device, setDevice] = useState<Device>("mobile");
  const [pane, setPane] = useState<"chat" | "preview">("chat"); // Phones show one at a time.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const turnList = useRef<HTMLOListElement>(null);
  const createdHere = useRef<string | null>(null);

  useEffect(() => {
    // An embed this editor just created is already on screen, mid-reply: don't reload it.
    if (embedId === null || embedId === createdHere.current) return;
    api.openEmbed(journalist, embedId).then(
      (opened) => {
        setEmbed(opened);
        setTurns(opened.messages);
        setVersions(opened.versions);
        setShownNumber(opened.latest_version?.number ?? null);
      },
      (e: Error) => setLoadError(e.message),
    );
  }, [journalist, embedId]);

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
    createdHere.current = created.id;
    setEmbed(opened);
    onCreated(created);
    return opened;
  }

  function updateModelTurn(update: (turn: Turn) => Turn) {
    setTurns((current) => [...current.slice(0, -1), update(current[current.length - 1])]);
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    setStreaming(true);
    setTurns((current) => [
      ...current,
      { role: "journalist", text: content, version_number: null, guides: [] },
      { role: "model", text: "", version_number: null, guides: [] },
    ]);

    try {
      const { id } = await ensureEmbed();
      const events = api.sendMessage(journalist, id, content, currentLanguage());
      for await (const { event, data } of events) {
        if (event === "title") {
          setEmbed((current) => current && { ...current, title: data.title });
          onChanged({ id, title: data.title });
        } else if (event === "guide") updateModelTurn((t) => ({ ...t, guides: [...t.guides, data.name] }));
        else if (event === "text") updateModelTurn((t) => ({ ...t, text: t.text + data.delta }));
        else if (event === "progress") setProgressHtml(data.html);
        else if (event === "version") {
          setVersions((current) => [...current, data]);
          setShownNumber(data.number);
          updateModelTurn((t) => ({ ...t, version_number: data.number }));
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

  async function publish(shown: Version) {
    if (!embed) return;
    const warnings = shown.findings.filter((f) => f.severity === "warn");
    if (warnings.length > 0 && !window.confirm(t("quality.confirm", { count: warnings.length }))) return;
    setPublishError(null);
    try {
      const updated = await api.publish(journalist, embed.id, shown.number, warnings.length > 0);
      setEmbed(updated);
      setVersions(updated.versions);
      onChanged({ id: embed.id, published: true });
    } catch (e) {
      setPublishError((e as Error).message);
    }
  }

  async function changeEmbedLanguage(embed_language: Language) {
    if (!embed) {
      setNewLanguage(embed_language);
      return;
    }
    const changed = await api.setEmbedLanguage(journalist, embed.id, embed_language);
    setEmbed((current) => current && { ...current, embed_language: changed.embed_language });
  }

  if (loadError) return <p className="error page-message">{loadError}</p>;
  if (embedId !== null && !embed) return <p className="hint page-message">{t("editor.loading")}</p>;

  const version = versions.find((v) => v.number === shownNumber) ?? null;
  const blocked = version?.findings.some((f) => f.severity === "block") ?? false;
  const latestNumber = versions.length ? versions[versions.length - 1].number : null;
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
          {turns.map((turn, i) => {
            const live = streaming && i === turns.length - 1; // The reply arriving right now.
            return (
            <li key={i} className={`turn ${turn.role}`}>
              {turn.guides.map((guide, g) => (
                <p key={g} className={live && !turn.text && g === turn.guides.length - 1 ? "status pulsing" : "status"}>
                  {t("editor.readingGuide", { name: t(`guides.${guide}`, { defaultValue: guide }) })}
                </p>
              ))}
              {turn.role === "model" ? <ChatMarkdown text={turn.text} /> : turn.text}
              {live && !turn.text && turn.guides.length === 0 && <p className="status pulsing">{t("editor.thinking")}</p>}
              {live && turn.text && progressHtml !== null && <p className="status pulsing">{t("editor.writing")}</p>}
              {turn.version_number !== null && (
                <button className="badge" onClick={() => setShownNumber(turn.version_number)}>
                  {t("editor.version", { number: turn.version_number })}
                </button>
              )}
              {turn.error && <p className="error">{turn.error}</p>}
            </li>
            );
          })}
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
              {t("editor.showing")}
              <select
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
          {version &&
            (version.published ? (
              <span className="published">{t("publish.published")}</span>
            ) : (
              <button
                className="primary"
                disabled={streaming || blocked}
                title={blocked ? t("quality.cannotPublish") : undefined}
                onClick={() => publish(version)}
              >
                {t("publish.publish", { number: version.number })}
              </button>
            ))}
          <div className="toggle" role="group" aria-label={t("editor.previewSize")}>
            {(["mobile", "desktop"] as const).map((d) => (
              <button
                key={d}
                className={device === d ? "on" : ""}
                aria-pressed={device === d}
                onClick={() => setDevice(d)}
              >
                {t(`editor.${d}`)}
              </button>
            ))}
          </div>
        </div>
        {version && !streaming && <Findings findings={version.findings} />}
        {publishError && <p className="error">{publishError}</p>}
        {embed?.delivery && (
          <details className="publish-details">
            <summary>{t("publish.heading")}</summary>
            <PublishPanel embed={embed} shown={version} />
          </details>
        )}
        <Preview
          versionUrl={version?.preview_url ?? null}
          progressFrameUrl={embed?.progress_frame_url ?? ""}
          progressHtml={progressHtml}
          device={device}
        />
      </section>
    </div>
  );
}

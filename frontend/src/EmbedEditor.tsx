import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Attachment, type Message, type OpenedEmbed, type Version } from "./api";
import { currentLanguage, type Language } from "./i18n";
import { LanguageSelect } from "./LanguagePicker";
import { Preview, type Device } from "./Preview";
import { Findings } from "./Findings";
import { Icon } from "./Icon";
import { PublishPanel } from "./PublishPanel";

interface Turn extends Message {
  error?: string;
}

export function EmbedEditor({ journalist, embedId }: { journalist: string; embedId: string }) {
  const { t } = useTranslation();
  const [embed, setEmbed] = useState<OpenedEmbed | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [shownNumber, setShownNumber] = useState<number | null>(null);
  const [progressHtml, setProgressHtml] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [device, setDevice] = useState<Device>("mobile");
  const [pane, setPane] = useState<"chat" | "preview">("chat"); // Phones show one at a time.
  const [loadError, setLoadError] = useState<string | null>(null);
  const turnList = useRef<HTMLOListElement>(null);

  useEffect(() => {
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
      const events = api.sendMessage(journalist, embedId, content, currentLanguage());
      for await (const { event, data } of events) {
        if (event === "guide")
          updateModelTurn((t) => ({ ...t, guides: [...t.guides, data.name] }));
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

  const version = versions.find((v) => v.number === shownNumber) ?? null;
  const blocked = version?.findings.some((f) => f.severity === "block") ?? false;
  const latestNumber = versions.length ? versions[versions.length - 1].number : null;

  const [publishError, setPublishError] = useState<string | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function attach(file: File) {
    setAttachError(null);
    setAttaching(true);
    try {
      const attachment: Attachment = await api.attach(journalist, embedId, file);
      setEmbed((current) => current && { ...current, attachments: [...current.attachments, attachment] });
    } catch (e) {
      setAttachError((e as Error).message);
    } finally {
      setAttaching(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function publish(shown: Version) {
    const warnings = shown.findings.filter((f) => f.severity === "warn");
    if (warnings.length > 0 && !window.confirm(t("quality.confirm", { count: warnings.length }))) return;
    setPublishError(null);
    try {
      const updated = await api.publish(journalist, embedId, shown.number, warnings.length > 0);
      setEmbed(updated);
      setVersions(updated.versions);
    } catch (e) {
      setPublishError((e as Error).message);
    }
  }

  async function changeEmbedLanguage(embed_language: Language) {
    const changed = await api.setEmbedLanguage(journalist, embedId, embed_language);
    setEmbed((current) => current && { ...current, embed_language: changed.embed_language });
  }

  if (loadError) return <p className="error">{loadError}</p>;
  if (!embed) return <p className="hint">{t("editor.loading")}</p>;

  return (
    <div className={`editor show-${pane}`}>
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
      <section className="chat card">
        <div className="chat-head">
          <h2>{embed.title}</h2>
          <span className="embed-language" title={t("editor.embedLanguageHint")}>
            {t("editor.embedLanguage")}
            <LanguageSelect
              value={embed.embed_language}
              onChange={changeEmbedLanguage}
              label={t("editor.embedLanguage")}
              disabled={streaming}
            />
          </span>
        </div>
        <ol className="turns" ref={turnList}>
          {turns.map((turn, i) => (
            <li key={i} className={`turn ${turn.role}`}>
              {turn.guides.map((guide, g) => (
                <p key={g} className="status">
                  {t("editor.readingGuide", { name: t(`guides.${guide}`, { defaultValue: guide }) })}
                </p>
              ))}
              {turn.text || (streaming && i === turns.length - 1 ? "…" : "")}
              {turn.version_number !== null && (
                <button className="badge" onClick={() => setShownNumber(turn.version_number)}>
                  {t("editor.version", { number: turn.version_number })}
                </button>
              )}
              {turn.error && <p className="error">{turn.error}</p>}
            </li>
          ))}
        </ol>
        {embed.attachments.length > 0 && (
          <ul className="attachments" aria-label={t("attachments.heading")}>
            {embed.attachments.map((a) => (
              <li key={a.id} title={a.columns?.map((c) => c.name).join(", ")}>
                {a.kind === "dataset" ? "📊" : "🖼"} {a.name}
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
            className="attach"
            title={t("attachments.attach")}
            aria-label={t("attachments.attach")}
            disabled={attaching || streaming}
            onClick={() => fileInput.current?.click()}
          >
            {attaching ? "…" : "📎"}
          </button>
          <textarea
            value={input}
            rows={3}
            placeholder={t("editor.placeholder")}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) send(e);
            }}
          />
          <button type="submit" className="primary" disabled={streaming || !input.trim()}>
            {t("editor.send")}
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
        {embed.delivery && (
          <details className="publish-details">
            <summary>{t("publish.heading")}</summary>
            <PublishPanel embed={embed} shown={version} />
          </details>
        )}
        <Preview
          versionUrl={version?.preview_url ?? null}
          progressFrameUrl={embed.progress_frame_url}
          progressHtml={progressHtml}
          device={device}
        />
      </section>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Message, type OpenedEmbed, type Version } from "./api";
import { currentLanguage, type Language } from "./i18n";
import { LanguageSelect } from "./LanguagePicker";
import { Preview, type Device } from "./Preview";
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
    turnList.current?.lastElementChild?.scrollIntoView({ block: "end" });
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
  const latestNumber = versions.length ? versions[versions.length - 1].number : null;

  const [publishError, setPublishError] = useState<string | null>(null);

  async function publish(number: number) {
    setPublishError(null);
    try {
      const updated = await api.publish(journalist, embedId, number);
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
    <div className="editor">
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
        <form className="composer" onSubmit={send}>
          <textarea
            value={input}
            rows={3}
            placeholder={t("editor.placeholder")}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) send(e);
            }}
          />
          <button type="submit" disabled={streaming || !input.trim()}>
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
              <button disabled={streaming} onClick={() => publish(version.number)}>
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
        <Preview
          versionUrl={version?.preview_url ?? null}
          progressFrameUrl={embed.progress_frame_url}
          progressHtml={progressHtml}
          device={device}
        />
        {publishError && <p className="error">{publishError}</p>}
        <PublishPanel embed={embed} shown={version} />
      </section>
    </div>
  );
}

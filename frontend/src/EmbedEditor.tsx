import { useEffect, useRef, useState } from "react";

import { api, type Message, type OpenedEmbed, type Version } from "./api";
import { Preview, type Device } from "./Preview";

interface Turn extends Message {
  error?: string;
}

export function EmbedEditor({ journalist, embedId }: { journalist: string; embedId: string }) {
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
      { role: "journalist", text: content, version_number: null },
      { role: "model", text: "", version_number: null },
    ]);

    try {
      for await (const { event, data } of api.sendMessage(journalist, embedId, content)) {
        if (event === "text") updateModelTurn((t) => ({ ...t, text: t.text + data.delta }));
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

  if (loadError) return <p className="error">{loadError}</p>;
  if (!embed) return <p className="hint">Loading…</p>;

  return (
    <div className="editor">
      <section className="chat card">
        <h2>{embed.title}</h2>
        <ol className="turns" ref={turnList}>
          {turns.map((turn, i) => (
            <li key={i} className={`turn ${turn.role}`}>
              {turn.text || (streaming && i === turns.length - 1 ? "…" : "")}
              {turn.version_number !== null && (
                <button className="badge" onClick={() => setShownNumber(turn.version_number)}>
                  Version {turn.version_number}
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
            placeholder="Describe what you want, or what to change…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) send(e);
            }}
          />
          <button type="submit" disabled={streaming || !input.trim()}>
            Send
          </button>
        </form>
      </section>

      <section className="preview card">
        <div className="preview-bar">
          {versions.length === 0 ? (
            <span>No version yet</span>
          ) : (
            <label className="version-picker">
              Showing
              <select
                value={shownNumber ?? ""}
                disabled={streaming}
                onChange={(e) => setShownNumber(Number(e.target.value))}
              >
                {[...versions].reverse().map((v) => (
                  <option key={v.number} value={v.number}>
                    Version {v.number}
                    {v.number === latestNumber ? " (latest)" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="toggle" role="group" aria-label="Preview size">
            {(["mobile", "desktop"] as const).map((d) => (
              <button
                key={d}
                className={device === d ? "on" : ""}
                aria-pressed={device === d}
                onClick={() => setDevice(d)}
              >
                {d === "mobile" ? "Mobile" : "Desktop"}
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
      </section>
    </div>
  );
}

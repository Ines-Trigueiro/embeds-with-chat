import { useEffect, useRef, useState } from "react";

export type Device = "mobile" | "desktop";

const WIDTHS: Record<Device, string> = { mobile: "375px", desktop: "100%" };

interface Props {
  versionUrl: string | null;
  draftFrameUrl: string;
  /** Half-written HTML while the model writes; null when not streaming. */
  draftHtml: string | null;
  device: Device;
}

/**
 * Both frames use the sandbox readers get (ADR 0001): scripts, but no same-origin access,
 * no top navigation and no popups. Content always comes from the embed origin.
 */
export function Preview({ versionUrl, draftFrameUrl, draftHtml, device }: Props) {
  const writing = draftHtml !== null;

  return (
    <div className="preview-stage">
      <div className="preview-device" style={{ width: WIDTHS[device] }}>
        {writing ? (
          <DraftFrame url={draftFrameUrl} html={draftHtml} />
        ) : versionUrl ? (
          <iframe
            key={versionUrl}
            className="preview-frame"
            sandbox="allow-scripts"
            src={versionUrl}
            title="Embed preview"
          />
        ) : (
          <p className="preview-empty">Describe the embed you want in the chat, and it appears here.</p>
        )}
        {writing && <div className="writing">Writing…</div>}
      </div>
    </div>
  );
}

function DraftFrame({ url, html }: { url: string; html: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.source === frame.current?.contentWindow && event.data?.type === "draft-frame-ready") {
        setReady(true);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    // The draft frame is sandboxed, so its origin is opaque: "*" is the only target that reaches it.
    if (ready) frame.current?.contentWindow?.postMessage({ type: "draft", html }, "*");
  }, [ready, html]);

  return (
    <iframe ref={frame} className="preview-frame" sandbox="allow-scripts" src={url} title="Draft preview" />
  );
}

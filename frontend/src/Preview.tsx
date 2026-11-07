import { useEffect, useRef, useState } from "react";

export type Device = "mobile" | "desktop";

const WIDTHS: Record<Device, string> = { mobile: "375px", desktop: "100%" };

interface Props {
  versionUrl: string | null;
  progressFrameUrl: string;
  /** Work in progress while the model writes its HTML; null otherwise. */
  progressHtml: string | null;
  device: Device;
}

/**
 * Both frames use the sandbox readers get (ADR 0001): scripts, but no same-origin access,
 * no top navigation and no popups. Content always comes from the embed origin.
 */
export function Preview({ versionUrl, progressFrameUrl, progressHtml, device }: Props) {
  const writing = progressHtml !== null;

  return (
    <div className="preview-stage">
      <div className="preview-device" style={{ width: WIDTHS[device] }}>
        {writing ? (
          <ProgressFrame url={progressFrameUrl} html={progressHtml} />
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

function ProgressFrame({ url, html }: { url: string; html: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.source === frame.current?.contentWindow && event.data?.type === "progress-frame-ready") {
        setReady(true);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    // The progress frame is sandboxed, so its origin is opaque: "*" is the only target that reaches it.
    if (ready) frame.current?.contentWindow?.postMessage({ type: "progress", html }, "*");
  }, [ready, html]);

  return (
    <iframe ref={frame} className="preview-frame" sandbox="allow-scripts" src={url} title="Work in progress" />
  );
}

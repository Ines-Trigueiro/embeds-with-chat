import { useEffect, useState } from "react";

import { forgetJournalist, storedJournalist, storeJournalist } from "./api";
import { EmbedEditor } from "./EmbedEditor";
import { JournalistPrompt } from "./JournalistPrompt";
import { MyEmbeds } from "./MyEmbeds";

/** "#/embeds/<id>" opens an embed; anything else is My embeds. Survives a reload. */
function embedIdFromHash(): string | null {
  return /^#\/embeds\/([\w-]+)$/.exec(window.location.hash)?.[1] ?? null;
}

export function App() {
  const [journalist, setJournalist] = useState(storedJournalist);
  const [embedId, setEmbedId] = useState(embedIdFromHash);

  useEffect(() => {
    const onHashChange = () => setEmbedId(embedIdFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  if (!journalist) {
    return (
      <JournalistPrompt
        onSubmit={(name) => {
          storeJournalist(name);
          setJournalist(name);
        }}
      />
    );
  }

  return (
    <div className={embedId ? "shell wide" : "shell"}>
      <header className="topbar">
        <h1>
          <a href="#/">Embeds with chat</a>
        </h1>
        <span className="who">
          {journalist}
          <button
            className="link"
            onClick={() => {
              forgetJournalist();
              setJournalist(null);
            }}
          >
            Switch journalist
          </button>
        </span>
      </header>
      <main>
        {embedId ? (
          <EmbedEditor key={embedId} journalist={journalist} embedId={embedId} />
        ) : (
          <MyEmbeds journalist={journalist} />
        )}
      </main>
    </div>
  );
}

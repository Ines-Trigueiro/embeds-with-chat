import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { forgetJournalist, storedJournalist, storeJournalist } from "./api";
import { EmbedEditor } from "./EmbedEditor";
import { JournalistPrompt } from "./JournalistPrompt";
import { LanguagePicker } from "./LanguagePicker";
import { MyEmbeds } from "./MyEmbeds";

/** "#/embeds/<id>" opens an embed; anything else is My embeds. Survives a reload. */
function embedIdFromHash(): string | null {
  return /^#\/embeds\/([\w-]+)$/.exec(window.location.hash)?.[1] ?? null;
}

export function App() {
  const { t } = useTranslation();
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
    <div className="app">
      <header className="topbar">
        <h1>
          <a href="#/">{t("app.title")}</a>
        </h1>
        <span className="who">
          <LanguagePicker />
          {journalist}
          <button
            className="link"
            onClick={() => {
              forgetJournalist();
              setJournalist(null);
            }}
          >
            {t("app.switchJournalist")}
          </button>
        </span>
      </header>
      <main className={embedId ? "main fill" : "main"}>
        {embedId ? (
          <EmbedEditor key={embedId} journalist={journalist} embedId={embedId} />
        ) : (
          <MyEmbeds journalist={journalist} />
        )}
      </main>
    </div>
  );
}

import { useState } from "react";

import { forgetJournalist, storedJournalist, storeJournalist } from "./api";
import { MyEmbeds } from "./MyEmbeds";
import { JournalistPrompt } from "./JournalistPrompt";

export function App() {
  const [journalist, setJournalist] = useState(storedJournalist);

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
    <div className="shell">
      <header className="topbar">
        <h1>Embeds with chat</h1>
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
        <MyEmbeds journalist={journalist} />
      </main>
    </div>
  );
}

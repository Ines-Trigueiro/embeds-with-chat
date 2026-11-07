import { useState } from "react";

import { forgetJournalist, storedJournalist, storeJournalist } from "./api";
import { MyEmbeds } from "./MyEmbeds";
import { UsernamePrompt } from "./UsernamePrompt";

export function App() {
  const [journalist, setJournalist] = useState(storedJournalist);

  if (!journalist) {
    return (
      <UsernamePrompt
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
            Switch user
          </button>
        </span>
      </header>
      <main>
        <MyEmbeds journalist={journalist} />
      </main>
    </div>
  );
}

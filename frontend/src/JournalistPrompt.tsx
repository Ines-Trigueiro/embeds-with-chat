import { useState } from "react";
import { useTranslation } from "react-i18next";

import { LanguagePicker } from "./LanguagePicker";

export function JournalistPrompt({ onSubmit }: { onSubmit: (name: string) => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const trimmed = name.trim();

  return (
    <form
      className="card prompt"
      onSubmit={(event) => {
        event.preventDefault();
        if (trimmed) onSubmit(trimmed);
      }}
    >
      <div className="prompt-head">
        <h1>{t("app.title")}</h1>
        <LanguagePicker />
      </div>
      <label>
        {t("prompt.yourName")}
        <input autoFocus value={name} maxLength={64} onChange={(e) => setName(e.target.value)} />
      </label>
      <p className="hint">{t("prompt.hint")}</p>
      <button type="submit" disabled={!trimmed}>
        {t("prompt.continue")}
      </button>
    </form>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "./Icon";
import { LanguagePicker } from "./LanguagePicker";

export function JournalistPrompt({ onSubmit }: { onSubmit: (name: string) => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const trimmed = name.trim();

  return (
    <div className="welcome">
      <form
        className="welcome-card"
        onSubmit={(event) => {
          event.preventDefault();
          if (trimmed) onSubmit(trimmed);
        }}
      >
        <div className="welcome-lang">
          <LanguagePicker />
        </div>
        <span className="logo" aria-hidden="true">
          <Icon name="sparkle" size={26} />
        </span>
        <h1>{t("app.title")}</h1>
        <p className="tagline">{t("prompt.tagline")}</p>
        <label className="field">
          <span>{t("prompt.yourName")}</span>
          <input
            autoFocus
            value={name}
            maxLength={64}
            placeholder={t("prompt.namePlaceholder")}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <button type="submit" className="primary big" disabled={!trimmed}>
          {t("prompt.continue")}
          <Icon name="send" />
        </button>
        <p className="fine-print">
          <Icon name="info" size={14} />
          {t("prompt.hint")}
        </p>
      </form>
    </div>
  );
}

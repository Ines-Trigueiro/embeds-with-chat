import { useTranslation } from "react-i18next";

import { changeLanguage, currentLanguage, LANGUAGE_NAMES, LANGUAGES, type Language } from "./i18n";

/** The journalist's language: the UI and the model's chat replies follow it. */
export function LanguagePicker() {
  const { t } = useTranslation();
  return (
    <select
      aria-label={t("app.language")}
      value={currentLanguage()}
      onChange={(e) => changeLanguage(e.target.value as Language)}
    >
      {LANGUAGES.map((language) => (
        <option key={language} value={language}>
          {LANGUAGE_NAMES[language]}
        </option>
      ))}
    </select>
  );
}

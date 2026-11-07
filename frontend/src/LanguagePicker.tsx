import { useTranslation } from "react-i18next";

import { changeLanguage, currentLanguage, LANGUAGE_NAMES, LANGUAGES, type Language } from "./i18n";

interface Props {
  value: Language;
  onChange: (language: Language) => void;
  label: string;
  disabled?: boolean;
}

export function LanguageSelect({ value, onChange, label, disabled }: Props) {
  return (
    <select
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as Language)}
    >
      {LANGUAGES.map((language) => (
        <option key={language} value={language}>
          {LANGUAGE_NAMES[language]}
        </option>
      ))}
    </select>
  );
}

/** The journalist's language: the UI and the model's chat replies follow it. */
export function LanguagePicker() {
  const { t } = useTranslation();
  return <LanguageSelect value={currentLanguage()} onChange={changeLanguage} label={t("app.language")} />;
}

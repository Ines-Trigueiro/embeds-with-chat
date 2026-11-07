import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Flag } from "./Flag";
import { Icon } from "./Icon";
import { changeLanguage, currentLanguage, LANGUAGE_NAMES, LANGUAGES, type Language } from "./i18n";

interface Props {
  value: Language;
  onChange: (language: Language) => void;
  label: string;
  disabled?: boolean;
  /** Show only the flag on the button; the list still names every language. */
  compact?: boolean;
}

/** A language dropdown with flags. A custom listbox, because <option> can't hold an SVG. */
export function LanguageSelect({ value, onChange, label, disabled, compact }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(LANGUAGES.indexOf(value));
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    list.current?.focus();
    function onPointerDown(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function show() {
    setActive(LANGUAGES.indexOf(value));
    setOpen(true);
  }

  function choose(language: Language) {
    setOpen(false);
    button.current?.focus();
    if (language !== value) onChange(language);
  }

  function onListKey(event: React.KeyboardEvent) {
    const last = LANGUAGES.length - 1;
    const keys: Record<string, () => void> = {
      ArrowDown: () => setActive((i) => Math.min(i + 1, last)),
      ArrowUp: () => setActive((i) => Math.max(i - 1, 0)),
      Home: () => setActive(0),
      End: () => setActive(last),
      Enter: () => choose(LANGUAGES[active]),
      " ": () => choose(LANGUAGES[active]),
      Escape: () => {
        setOpen(false);
        button.current?.focus();
      },
      Tab: () => setOpen(false),
    };
    const action = keys[event.key];
    if (!action) return;
    if (event.key !== "Tab") event.preventDefault();
    action();
  }

  return (
    <div className={`lang-select${compact ? " compact" : ""}`} ref={root}>
      <button
        ref={button}
        type="button"
        className="lang-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={`${label}: ${LANGUAGE_NAMES[value]}`}
        title={label}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            show();
          }
        }}
      >
        <Flag language={value} />
        {!compact && <span>{LANGUAGE_NAMES[value]}</span>}
        <Icon name="chevronDown" size={14} />
      </button>
      {open && (
        <ul
          ref={list}
          id={listId}
          className="lang-list"
          role="listbox"
          tabIndex={-1}
          aria-label={label}
          aria-activedescendant={`${listId}-${LANGUAGES[active]}`}
          onKeyDown={onListKey}
        >
          {LANGUAGES.map((language, i) => (
            <li
              key={language}
              id={`${listId}-${language}`}
              role="option"
              aria-selected={language === value}
              className={i === active ? "active" : undefined}
              onPointerEnter={() => setActive(i)}
              onClick={() => choose(language)}
            >
              <Flag language={language} />
              <span>{LANGUAGE_NAMES[language]}</span>
              {language === value && <Icon name="check" size={14} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The journalist's language: the UI and the model's chat replies follow it. */
export function LanguagePicker({ compact }: { compact?: boolean }) {
  const { t } = useTranslation();
  return (
    <LanguageSelect
      value={currentLanguage()}
      onChange={changeLanguage}
      label={t("app.language")}
      compact={compact}
    />
  );
}

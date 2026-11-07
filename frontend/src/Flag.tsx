import { useId } from "react";

import type { Language } from "./i18n";

// Inline SVG flags: flag emoji don't render on Windows.

function Norway() {
  return (
    <svg viewBox="0 0 22 16" preserveAspectRatio="xMidYMid slice">
      <rect width="22" height="16" fill="#ba0c2f" />
      <path d="M6 0h4v16H6zM0 6h22v4H0z" fill="#fff" />
      <path d="M7 0h2v16H7zM0 7h22v2H0z" fill="#00205b" />
    </svg>
  );
}

function Denmark() {
  return (
    <svg viewBox="0 0 37 28" preserveAspectRatio="xMidYMid slice">
      <rect width="37" height="28" fill="#c8102e" />
      <path d="M12 0h4v28h-4zM0 12h37v4H0z" fill="#fff" />
    </svg>
  );
}

function UnitedKingdom() {
  const clip = useId();
  return (
    <svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice">
      <clipPath id={clip}>
        <path d="M30 15h30v15zv15H0zH0V0zV0h30z" />
      </clipPath>
      <rect width="60" height="30" fill="#012169" />
      <path d="M0 0l60 30M60 0 0 30" stroke="#fff" strokeWidth="6" />
      <path d="M0 0l60 30M60 0 0 30" clipPath={`url(#${clip})`} stroke="#c8102e" strokeWidth="4" />
      <path d="M30 0v30M0 15h60" stroke="#fff" strokeWidth="10" />
      <path d="M30 0v30M0 15h60" stroke="#c8102e" strokeWidth="6" />
    </svg>
  );
}

const FLAGS: Record<Language, () => React.JSX.Element> = { nb: Norway, da: Denmark, en: UnitedKingdom };

export function Flag({ language }: { language: Language }) {
  const Shape = FLAGS[language];
  return (
    <span className="flag" aria-hidden="true">
      <Shape />
    </span>
  );
}

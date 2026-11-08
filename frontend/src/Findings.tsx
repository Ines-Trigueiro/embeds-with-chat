import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Finding } from "./api";
import { Icon } from "./Icon";

/** Blockers stop publishing; warnings need the journalist to accept them. */
export function bySeverity(findings: Finding[]) {
  return {
    blockers: findings.filter((f) => f.severity === "block"),
    warnings: findings.filter((f) => f.severity === "warn"),
  };
}

/** The quality check's findings for the version on screen, in the journalist's language. */
export function Findings({ findings }: { findings: Finding[] }) {
  const { t } = useTranslation();
  return (
    <ul className="findings">
      {findings.map((finding, i) => (
        <li key={i} className={finding.severity}>
          <strong>{finding.severity === "block" ? t("quality.block") : t("quality.warn")}</strong>{" "}
          {t(`quality.rules.${finding.rule}`, { detail: finding.detail, defaultValue: finding.rule })}
        </li>
      ))}
    </ul>
  );
}

/** The quality check at a glance: one chip per severity, opening the details on click. */
export function FindingChips({ findings }: { findings: Finding[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const { blockers, warnings } = bySeverity(findings);

  if (findings.length === 0) {
    return (
      <div className="chips">
        <span className="chip ok">
          <Icon name="check" size={14} />
          {t("quality.chipOk")}
        </span>
      </div>
    );
  }
  const chips = [
    { severity: "block", icon: "blocker", label: "quality.chipBlock", count: blockers.length },
    { severity: "warn", icon: "warning", label: "quality.chipWarn", count: warnings.length },
  ] as const;
  return (
    <div className="chips-wrap">
      <div className="chips">
        {chips.map(
          ({ severity, icon, label, count }) =>
            count > 0 && (
              <button key={severity} className={`chip ${severity}`} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
                <Icon name={icon} size={14} />
                {t(label, { count })}
              </button>
            ),
        )}
      </div>
      {open && <Findings findings={findings} />}
    </div>
  );
}

import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Finding } from "./api";
import { Icon } from "./Icon";

/** The quality check's findings for the version on screen, in the journalist's language. */
export function Findings({ findings }: { findings: Finding[] }) {
  const { t } = useTranslation();
  if (findings.length === 0) return <p className="findings ok">{t("quality.ok")}</p>;

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
  const blockers = findings.filter((f) => f.severity === "block").length;
  const warnings = findings.length - blockers;

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
  return (
    <div className="chips-wrap">
      <div className="chips">
        {blockers > 0 && (
          <button className="chip block" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            <Icon name="blocker" size={14} />
            {t("quality.chipBlock", { count: blockers })}
          </button>
        )}
        {warnings > 0 && (
          <button className="chip warn" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            <Icon name="warning" size={14} />
            {t("quality.chipWarn", { count: warnings })}
          </button>
        )}
      </div>
      {open && <Findings findings={findings} />}
    </div>
  );
}

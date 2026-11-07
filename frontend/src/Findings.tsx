import { useTranslation } from "react-i18next";

import type { Finding } from "./api";

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

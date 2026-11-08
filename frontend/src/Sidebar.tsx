import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Embed } from "./api";
import { RenameButton, TitleInput } from "./EditableTitle";
import { Icon } from "./Icon";
import { LanguagePicker } from "./LanguagePicker";

interface Props {
  journalist: string;
  embeds: Embed[] | null;
  currentId: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onRename: (embedId: string, title: string) => void;
  onSwitchJournalist: () => void;
  /** Phones: the sidebar is a drawer, closed after picking an embed. */
  onNavigate: () => void;
}

/** The journalist's embeds, like the chat list of an LLM app. */
export function Sidebar(props: Props) {
  const { journalist, embeds, currentId, collapsed, onToggle, onRename, onSwitchJournalist, onNavigate } = props;
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [renaming, setRenaming] = useState<string | null>(null);

  const needle = query.trim().toLocaleLowerCase();
  const shown = needle ? embeds?.filter((e) => e.title?.toLocaleLowerCase().includes(needle)) ?? null : embeds;

  return (
    <nav className={`sidebar${collapsed ? " collapsed" : ""}`} aria-label={t("sidebar.heading")}>
      <div className="sidebar-head">
        {!collapsed && (
          <a className="brand" href="#/" onClick={onNavigate}>
            <span className="logo small" aria-hidden="true">
              <Icon name="sparkle" size={16} />
            </span>
            {t("app.title")}
          </a>
        )}
        <button
          className="ghost icon-only"
          title={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
          aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
          aria-expanded={!collapsed}
          onClick={onToggle}
        >
          <Icon name="sidebar" />
        </button>
      </div>

      <a
        className={`new-embed${currentId === null ? " current" : ""}`}
        href="#/"
        title={t("sidebar.new")}
        onClick={onNavigate}
      >
        <Icon name="plus" />
        {!collapsed && <span>{t("sidebar.new")}</span>}
      </a>

      {!collapsed && (
        <>
          <label className="search">
            <Icon name="search" size={16} />
            <input
              type="search"
              value={query}
              placeholder={t("sidebar.search")}
              aria-label={t("sidebar.search")}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>

          <ul className="embed-items">
            {shown === null ? (
              <li className="hint">{t("sidebar.loading")}</li>
            ) : shown.length === 0 ? (
              <li className="hint">{query ? t("sidebar.noMatch") : t("sidebar.empty")}</li>
            ) : (
              shown.map((embed) => (
                <li key={embed.id} className="embed-item">
                  {renaming === embed.id ? (
                    <TitleInput
                      initial={embed.title}
                      onDone={(title) => {
                        setRenaming(null);
                        if (title) onRename(embed.id, title);
                      }}
                    />
                  ) : (
                    <>
                      <a
                        href={`#/embeds/${embed.id}`}
                        className={embed.id === currentId ? "current" : undefined}
                        aria-current={embed.id === currentId ? "page" : undefined}
                        onClick={onNavigate}
                        onDoubleClick={(e) => {
                          e.preventDefault();
                          setRenaming(embed.id);
                        }}
                      >
                        <span
                          className={`dot${embed.published ? " on" : ""}`}
                          role={embed.published ? "img" : undefined}
                          aria-label={embed.published ? t("publish.published") : undefined}
                          title={embed.published ? t("publish.published") : undefined}
                        />
                        <span className={embed.title ? "item-title" : "item-title untitled"}>
                          {embed.title ?? t("sidebar.new")}
                        </span>
                        <RelativeTime iso={embed.created_at} />
                      </a>
                      <RenameButton title={embed.title} onClick={() => setRenaming(embed.id)} />
                    </>
                  )}
                </li>
              ))
            )}
          </ul>
        </>
      )}

      <div className="sidebar-foot">
        <span className="avatar" title={journalist} aria-hidden="true">
          {journalist.trim().charAt(0).toLocaleUpperCase()}
        </span>
        {!collapsed && <span className="who-name">{journalist}</span>}
        <LanguagePicker compact />
        <button
          className="ghost icon-only"
          title={t("app.switchJournalist")}
          aria-label={t("app.switchJournalist")}
          onClick={onSwitchJournalist}
        >
          <Icon name="logout" />
        </button>
      </div>
    </nav>
  );
}

/** Up to which age (in minutes) a unit is used, and how many minutes it has. */
const UNITS = [
  [60, "minute", 1],
  [60 * 24, "hour", 60],
  [60 * 24 * 30, "day", 60 * 24],
] as const;

function RelativeTime({ iso }: { iso: string }) {
  const { i18n } = useTranslation();
  const date = new Date(iso);
  const minutes = Math.round((date.getTime() - Date.now()) / 60_000);
  const unit = UNITS.find(([upTo]) => Math.abs(minutes) < upTo);
  const text = unit
    ? new Intl.RelativeTimeFormat(i18n.language, { numeric: "auto", style: "short" }).format(
        Math.round(minutes / unit[2]),
        unit[1],
      )
    : date.toLocaleDateString(i18n.language);
  return (
    <time dateTime={iso} title={date.toLocaleString(i18n.language)}>
      {text}
    </time>
  );
}

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "./Icon";

/** Editing a Title: Enter or leaving the field saves, Escape cancels. */
export function TitleInput({ initial, onDone }: { initial: string | null; onDone: (title: string | null) => void }) {
  const { t } = useTranslation();
  const [edited, setEdited] = useState(initial ?? "");
  const finished = useRef(false); // Enter, then the blur as the field goes away: save once.

  function finish(save: boolean) {
    if (finished.current) return;
    finished.current = true;
    const trimmed = edited.trim();
    onDone(save && trimmed && trimmed !== initial ? trimmed : null);
  }

  return (
    <input
      className="title-input"
      autoFocus
      value={edited}
      maxLength={200}
      aria-label={t("sidebar.rename")}
      onChange={(e) => setEdited(e.target.value)}
      onFocus={(e) => e.target.select()}
      onBlur={() => finish(true)}
      onKeyDown={(e) => {
        if (e.key === "Enter") finish(true);
        if (e.key === "Escape") finish(false);
      }}
    />
  );
}

/** The Title in the editor header: double-click or the pencil to rename. */
export function EditableTitle({ title, onRename }: { title: string | null; onRename: (title: string) => void }) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <TitleInput
        initial={title}
        onDone={(renamed) => {
          setEditing(false);
          if (renamed) onRename(renamed);
        }}
      />
    );
  }
  return (
    <span className="editable-title">
      <h2 className={title ? undefined : "untitled"} title={title ?? undefined} onDoubleClick={() => setEditing(true)}>
        {title ?? t("sidebar.untitled")}
      </h2>
      <button
        type="button"
        className="ghost icon-only rename"
        title={t("sidebar.rename")}
        aria-label={t("sidebar.rename")}
        onClick={() => setEditing(true)}
      >
        <Icon name="pencil" size={15} />
      </button>
    </span>
  );
}

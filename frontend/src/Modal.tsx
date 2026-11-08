import { useEffect, useId, useRef } from "react";

import { Icon } from "./Icon";

interface Props {
  title: React.ReactNode;
  /** The label of a close button in the header; without one, there is none. */
  closeLabel?: string;
  small?: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

/**
 * A native modal <dialog>: focus stays inside, and Escape, the backdrop or `onClose`
 * close it. It starts on the first enabled primary button, not on whatever the browser picks.
 */
export function Modal({ title, closeLabel, small, onClose, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    // Unmounting removes the dialog, so there is nothing to clean up (and StrictMode's
    // second run finds it already open).
    const element = dialog.current;
    if (!element || element.open) return;
    element.showModal();
    element.querySelector<HTMLElement>(".dialog-body .primary:enabled")?.focus();
  }, []);

  return (
    <dialog
      ref={dialog}
      className={small ? "dialog small" : "dialog"}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()} // A click on the backdrop.
    >
      <div className="dialog-head">
        <h2 id={titleId}>{title}</h2>
        {closeLabel && (
          <button className="ghost icon-only" title={closeLabel} aria-label={closeLabel} onClick={onClose}>
            <Icon name="close" />
          </button>
        )}
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>
  );
}

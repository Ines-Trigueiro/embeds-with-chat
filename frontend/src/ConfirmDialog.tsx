import { useEffect, useRef } from "react";

interface Props {
  title: string;
  children: React.ReactNode;
  confirm: string;
  cancel: string;
  onConfirm: () => void;
  onClose: () => void;
}

/** A small modal question: Escape, Cancel or the backdrop close it. */
export function ConfirmDialog({ title, children, confirm, cancel, onConfirm, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element || element.open) return;
    element.showModal();
    element.querySelector<HTMLElement>(".dialog-actions .primary")?.focus();
  }, []);

  return (
    <dialog
      ref={dialog}
      className="dialog small"
      aria-labelledby="confirm-title"
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && dialog.current.close()}
    >
      <div className="dialog-head">
        <h2 id="confirm-title">{title}</h2>
      </div>
      <div className="dialog-body">
        {children}
        <div className="dialog-actions">
          <button onClick={() => dialog.current?.close()}>{cancel}</button>
          <button
            className="primary"
            onClick={() => {
              onConfirm();
              dialog.current?.close();
            }}
          >
            {confirm}
          </button>
        </div>
      </div>
    </dialog>
  );
}

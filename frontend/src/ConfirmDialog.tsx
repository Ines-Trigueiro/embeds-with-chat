import { Modal } from "./Modal";

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
  return (
    <Modal title={title} small onClose={onClose}>
      {children}
      <div className="dialog-actions">
        <button onClick={onClose}>{cancel}</button>
        <button
          className="primary"
          onClick={() => {
            onConfirm();
            onClose();
          }}
        >
          {confirm}
        </button>
      </div>
    </Modal>
  );
}

import { btnDanger, btnSecondary } from "../utils/styles";

export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", onConfirm, onClose, loading }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className={btnSecondary} onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className={btnDanger} onClick={onConfirm} disabled={loading}>
            {loading ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

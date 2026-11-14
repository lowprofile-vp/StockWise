import { useEffect } from "react";

export default function Modal({ open, title, onClose, children, wide = false }) {
  useEffect(() => {
    if (!open) return undefined;
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center">
      <button type="button" aria-label="Close dialog" className="absolute inset-0 cursor-default" onClick={onClose} />
      <div className={`relative max-h-[90vh] w-full overflow-auto rounded-xl bg-white p-5 shadow-xl ${wide ? "max-w-3xl" : "max-w-lg"}`}>
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

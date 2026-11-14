export default function Pagination({ meta, onPage }) {
  if (!meta || meta.total <= meta.per_page) return null;
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
      <p>
        Page {meta.page} of {meta.pages} · {meta.total} records
      </p>
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40" disabled={meta.page <= 1} onClick={() => onPage(meta.page - 1)}>
          Previous
        </button>
        <button type="button" className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40" disabled={meta.page >= meta.pages} onClick={() => onPage(meta.page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}

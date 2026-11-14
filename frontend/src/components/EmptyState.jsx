export default function EmptyState({ title, body, action }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
      <p className="font-medium text-slate-800">{title}</p>
      {body ? <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{body}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

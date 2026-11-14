export default function ChartCard({ title, subtitle, children, action }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-1 text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="h-72 w-full">{children}</div>
    </section>
  );
}

export default function StatCard({ label, value, hint, tone = "slate" }) {
  const tones = {
    slate: "text-slate-900",
    green: "text-emerald-700",
    amber: "text-amber-700",
    red: "text-red-700",
  };
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tracking-tight ${tones[tone] || tones.slate}`}>{value}</p>
      {hint ? <p className="mt-2 text-xs leading-5 text-slate-500">{hint}</p> : null}
    </article>
  );
}

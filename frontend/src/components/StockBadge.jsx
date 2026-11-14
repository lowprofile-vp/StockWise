const styles = {
  Healthy: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  "Low Stock": "bg-amber-50 text-amber-800 ring-amber-200",
  Critical: "bg-red-50 text-red-800 ring-red-200",
  "Out of Stock": "bg-red-100 text-red-900 ring-red-300",
};

export default function StockBadge({ status }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles[status] || "bg-slate-100 text-slate-700 ring-slate-200"}`}>
      {status || "Unknown"}
    </span>
  );
}

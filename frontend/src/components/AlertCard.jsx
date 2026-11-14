import { Link } from "react-router-dom";
import StockBadge from "./StockBadge";
import UrgencyBadge from "./UrgencyBadge";
import { formatDays, formatQty } from "../utils/format";

export default function AlertCard({ item }) {
  return (
    <Link to={`/inventory/${item.product_id}`} className="block rounded-lg border border-slate-200 px-3 py-3 transition hover:border-teal-700 hover:bg-teal-50/40">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900">{item.name}</p>
          <p className="mt-1 text-xs text-slate-500">
            {formatQty(item.current_stock, item.unit)} on hand · {formatDays(item.days_until_stockout)} of cover
          </p>
        </div>
        <UrgencyBadge urgency={item.urgency} />
      </div>
      <p className="mt-2 text-sm leading-5 text-slate-600">{item.reason}</p>
      <div className="mt-2">
        <StockBadge status={item.stock_status} />
      </div>
    </Link>
  );
}

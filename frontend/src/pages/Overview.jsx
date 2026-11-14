import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import AlertCard from "../components/AlertCard";
import ChartCard from "../components/ChartCard";
import Spinner from "../components/Spinner";
import UrgencyBadge from "../components/UrgencyBadge";
import { formatDateTime, formatDays, formatMoney, formatQty, titleCase } from "../utils/format";

export default function Overview() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [range, setRange] = useState("daily");

  useEffect(() => {
    api.get("/analytics/overview")
      .then((response) => setData(response.data.data))
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (error) return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!data) return <Spinner label="Loading the overview" />;

  const cards = data.cards;
  const chart = data.demand[range] || [];
  const labelKey = range === "daily" ? "date" : "label";

  return (
    <div>
      <PageHeader title="Overview" subtitle={`${user.business_name} · figures are calculated from current stock and recorded movement.`} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Total products" value={cards.total_products} />
        <StatCard label="Inventory value" value={formatMoney(cards.inventory_value, cards.currency)} hint={data.definitions.inventory_value} />
        <StatCard label="Low-stock products" value={cards.low_stock_products} tone="amber" hint={data.definitions.low_stock_products} />
        <StatCard label="Critical stockout risk" value={cards.critical_stockout_risk} tone="red" hint={data.definitions.critical_stockout_risk} />
        <StatCard label="Pending purchase orders" value={cards.pending_purchase_orders} />
        <StatCard label="Restocking budget" value={formatMoney(cards.restock_budget, cards.currency)} tone="green" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <AlertColumn title="Critical" items={data.alerts.critical} empty="No products are expected to run out before delivery." />
        <AlertColumn title="Low stock" items={data.alerts.low_stock} empty="No products are sitting at the minimum without a lead-time risk." />
        <AlertColumn title="Approaching reorder point" items={data.alerts.approaching_reorder} empty="No product is inside its safety buffer." />
      </div>

      <div className="mt-6">
        <ChartCard
          title="Demand overview"
          subtitle={data.demand.value_basis}
          action={
            <div className="flex rounded-lg border border-slate-200 p-1 text-xs">
              {["daily", "weekly", "monthly"].map((key) => (
                <button key={key} type="button" onClick={() => setRange(key)} className={`rounded-md px-2 py-1 ${range === key ? "bg-navy-900 text-white" : "text-slate-600"}`}>
                  {titleCase(key)}
                </button>
              ))}
            </div>
          }
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chart}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey={labelKey} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => formatMoney(value, cards.currency)} />
              <Area type="monotone" dataKey="value" stroke="#0f766e" fill="#ccfbf1" name="Consumed value" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Restocking priorities</h2>
            <Link to="/restock" className="text-sm font-medium text-teal-800">Open restock center</Link>
          </div>
          <div className="space-y-3">
            {data.priorities.length ? data.priorities.map((item) => (
              <Link key={item.product_id} to={`/inventory/${item.product_id}`} className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 px-3 py-2 hover:bg-slate-50">
                <div>
                  <p className="font-medium text-slate-900">{item.name}</p>
                  <p className="text-xs text-slate-500">Stockout {formatDays(item.days_until_stockout)} · order {formatQty(item.suggested_quantity, item.unit)}</p>
                </div>
                <UrgencyBadge urgency={item.urgency} />
              </Link>
            )) : <p className="text-sm text-slate-500">No paid restock is recommended.</p>}
          </div>
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 font-semibold text-slate-900">Recent activity</h2>
          <div className="space-y-3">
            {data.activity.map((item) => (
              <Link key={item.id} to={item.href} className="block rounded-lg px-2 py-1 hover:bg-slate-50">
                <p className="text-sm font-medium text-slate-800">{item.title}</p>
                <p className="text-xs text-slate-500">{item.detail} · {formatDateTime(item.timestamp)}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function AlertColumn({ title, items, empty }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 font-semibold text-slate-900">{title}</h2>
      <div className="space-y-3">
        {items.length ? items.map((item) => <AlertCard key={item.product_id} item={item} />) : <p className="text-sm text-slate-500">{empty}</p>}
      </div>
    </section>
  );
}

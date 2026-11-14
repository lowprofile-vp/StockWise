import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import UrgencyBadge from "../components/UrgencyBadge";
import Modal from "../components/Modal";
import Spinner from "../components/Spinner";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";
import { formatDate, formatDays, formatMoney, formatQty, titleCase } from "../utils/format";

export default function RestockCenter() {
  const { user } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState("recommendations");
  const [recs, setRecs] = useState(null);
  const [selected, setSelected] = useState(null);
  const [budget, setBudget] = useState(user.restock_budget || 10000);
  const [plan, setPlan] = useState(null);
  const [orders, setOrders] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [receiveOrder, setReceiveOrder] = useState(null);
  const [draft, setDraft] = useState({ supplier_id: "", items: [{ product_id: "", quantity: "", unit_cost: "" }] });

  async function load() {
    setLoading(true);
    try {
      const [recommendationResponse, orderResponse, supplierResponse, productResponse] = await Promise.all([
        api.get("/restock/recommendations"),
        api.get("/restock/purchase-orders"),
        api.get("/suppliers", { params: { include_inactive: false } }),
        api.get("/products", { params: { per_page: 100, sort: "name" } }),
      ]);
      setRecs(recommendationResponse.data);
      setOrders(orderResponse.data.data);
      setSuppliers(supplierResponse.data.data);
      setProducts(productResponse.data.data);
      if (!selected && recommendationResponse.data.data[0]) setSelected(recommendationResponse.data.data[0]);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function optimize() {
    setWorking(true);
    try {
      const response = await api.post("/restock/optimize", { budget });
      setPlan(response.data.data);
      setTab("planner");
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setWorking(false);
    }
  }

  async function createFrom(source) {
    const groups = new Map();
    source.selected.forEach((item) => {
      if (!item.supplier_id) return;
      const list = groups.get(item.supplier_id) || [];
      list.push(item);
      groups.set(item.supplier_id, list);
    });
    if (!groups.size) {
      toast.push("Selected lots need a supplier before an order can be created.", "error");
      return;
    }
    setWorking(true);
    try {
      for (const [supplierId, items] of groups) {
        await api.post("/restock/purchase-orders", {
          supplier_id: Number(supplierId),
          approve: true,
          items: items.map((item) => ({
            product_id: item.product_id,
            quantity: item.suggested_quantity,
            unit_cost: item.exact_cost && item.suggested_quantity ? Number(item.exact_cost) / Number(item.suggested_quantity) : undefined,
          })),
        });
      }
      toast.push("Approved purchase orders were created. Stock is unchanged until a delivery is received.");
      setPlan(null);
      await load();
      setTab("orders");
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setWorking(false);
    }
  }

  async function setStatus(order, status) {
    try {
      await api.put(`/restock/purchase-orders/${order.order_id}`, { status });
      toast.push(`Order ${order.code} is now ${titleCase(status)}.`);
      load();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function submitDraft(event) {
    event.preventDefault();
    try {
      await api.post("/restock/purchase-orders", {
        supplier_id: Number(draft.supplier_id),
        approve: false,
        items: draft.items.filter((item) => item.product_id).map((item) => ({
          product_id: Number(item.product_id),
          quantity: item.quantity,
          unit_cost: item.unit_cost || undefined,
        })),
      });
      toast.push("Draft purchase order saved.");
      setDraft({ supplier_id: "", items: [{ product_id: "", quantity: "", unit_cost: "" }] });
      load();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function receive(event) {
    event.preventDefault();
    const items = receiveOrder.items
      .filter((item) => Number(item.receive_now) > 0)
      .map((item) => ({ id: item.id, quantity: item.receive_now }));
    try {
      await api.post(`/restock/purchase-orders/${receiveOrder.order_id}/receive`, { items });
      toast.push("Delivery recorded and inventory updated.");
      setReceiveOrder(null);
      load();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  if (loading) return <Spinner label="Loading restock center" />;

  return (
    <div>
      <PageHeader title="Restock Center" subtitle="Urgency comes from days of cover versus supplier lead time. Orders are created only when you approve them." />
      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ["recommendations", "Recommendations"],
          ["planner", "Budget planner"],
          ["orders", "Purchase orders"],
        ].map(([id, label]) => (
          <button key={id} type="button" onClick={() => setTab(id)} className={`rounded-full px-3 py-1.5 text-sm ${tab === id ? "bg-navy-900 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200"}`}>{label}</button>
        ))}
      </div>

      {tab === "recommendations" && recs ? (
        <div className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <DataTable
              columns={[
                { key: "name", label: "Product" },
                { key: "current_stock", label: "Stock", render: (row) => formatQty(row.current_stock, row.unit) },
                { key: "average_daily_demand", label: "Daily use", render: (row) => formatQty(row.average_daily_demand, row.unit) },
                { key: "days_until_stockout", label: "Cover", render: (row) => formatDays(row.days_until_stockout) },
                { key: "lead_time_days", label: "Lead time", render: (row) => `${row.lead_time_days}d` },
                { key: "suggested_quantity", label: "Reorder", render: (row) => formatQty(row.suggested_quantity, row.unit) },
                { key: "estimated_cost", label: "Cost", render: (row) => formatMoney(row.estimated_cost, user.currency) },
                { key: "urgency", label: "Urgency", render: (row) => <UrgencyBadge urgency={row.urgency} /> },
              ]}
              rows={recs.data}
              rowKey="product_id"
              onRow={setSelected}
              emptyTitle="No active products"
            />
          </div>
          <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            {selected ? (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">{selected.name}</h2>
                  <UrgencyBadge urgency={selected.urgency} />
                </div>
                <dl className="mt-3 space-y-2 text-sm">
                  <Row label="Current quantity" value={formatQty(selected.current_stock, selected.unit)} />
                  <Row label="Average daily demand" value={formatQty(selected.average_daily_demand, selected.unit)} />
                  <Row label="Supplier lead time" value={`${selected.lead_time_days} days${selected.supplier_name ? ` · ${selected.supplier_name}` : ""}`} />
                  <Row label="Estimated stockout" value={formatDays(selected.days_until_stockout)} />
                  <Row label="Reorder point" value={formatQty(selected.reorder_point, selected.unit)} />
                  <Row label="Recommended quantity" value={formatQty(selected.suggested_quantity, selected.unit)} />
                  <Row label="Estimated cost" value={formatMoney(selected.estimated_cost, user.currency)} />
                </dl>
                <p className="mt-3 text-sm leading-6 text-slate-600">{selected.reason}</p>
                {selected.data_warning ? <p className="mt-2 text-sm text-amber-800">{selected.data_warning}</p> : null}
                <Link className="mt-3 inline-block text-sm font-medium text-teal-800" to={`/inventory/${selected.product_id}`}>Open product</Link>
              </>
            ) : <p className="text-sm text-slate-500">Select a product.</p>}
            <details className="mt-4 text-sm text-slate-600">
              <summary className="cursor-pointer font-medium text-slate-800">How the score is calculated</summary>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {recs.formula ? Object.entries(recs.formula).map(([key, text]) => <li key={key}><span className="font-medium">{titleCase(key)}:</span> {text}</li>) : null}
              </ul>
            </details>
          </aside>
        </div>
      ) : null}

      {tab === "planner" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-end gap-3">
            <label>
              <span className={labelClass}>Available budget ({user.currency})</span>
              <input className={inputClass} type="number" min="0" step="1" value={budget} onChange={(event) => setBudget(event.target.value)} />
            </label>
            <button className={btnPrimary} onClick={optimize} disabled={working}>{working ? "Planning..." : "Compare plans"}</button>
          </div>
          {plan ? (
            <>
              <p className="mt-4 text-sm leading-6 text-slate-600">{plan.comparison.note} {plan.currency_rounding}</p>
              <p className="mt-2 text-sm text-slate-700">
                Greedy score {plan.comparison.greedy_value} · optimal score {plan.comparison.optimal_value}.
                {plan.comparison.same_selection ? " Both methods selected the same lots." : " The selections differ."}
                {plan.comparison.budget_covers_all_critical ? " The budget can cover every critical lot." : ` Critical lots together cost ${formatMoney(plan.comparison.critical_lot_cost, user.currency)}.`}
              </p>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <PlanColumn title="Greedy heuristic" plan={plan.greedy} currency={user.currency} />
                <PlanColumn title="Dynamic programming" plan={plan.dynamic_programming} currency={user.currency} />
              </div>
              {user.permissions?.approve_orders ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button className={btnPrimary} disabled={working} onClick={() => createFrom(plan.dynamic_programming)}>Approve optimal plan</button>
                  <button className={btnSecondary} disabled={working} onClick={() => createFrom(plan.greedy)}>Approve greedy plan</button>
                </div>
              ) : <p className="mt-4 text-sm text-slate-500">Staff can generate the plan. Only the owner can approve purchase orders.</p>}
            </>
          ) : <p className="mt-4 text-sm text-slate-500">Enter a budget such as 10000 to see which recommended lots fit.</p>}
        </section>
      ) : null}

      {tab === "orders" ? (
        <div className="space-y-4">
          <form onSubmit={submitDraft} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="font-semibold text-slate-900">New draft order</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-4">
              <select className={inputClass} required value={draft.supplier_id} onChange={(event) => setDraft({ ...draft, supplier_id: event.target.value })} aria-label="Supplier">
                <option value="">Supplier</option>
                {suppliers.map((supplier) => <option key={supplier.supplier_id} value={supplier.supplier_id}>{supplier.name}</option>)}
              </select>
              {draft.items.map((item, index) => (
                <div key={index} className="contents">
                  <select className={inputClass} aria-label="Product" value={item.product_id} onChange={(event) => {
                    const items = draft.items.map((row, rowIndex) => rowIndex === index ? { ...row, product_id: event.target.value } : row);
                    setDraft({ ...draft, items });
                  }}>
                    <option value="">Product</option>
                    {products.map((product) => <option key={product.product_id} value={product.product_id}>{product.name}</option>)}
                  </select>
                  <input className={inputClass} type="number" min="0" step="any" placeholder="Quantity" aria-label="Quantity" value={item.quantity} onChange={(event) => {
                    const items = draft.items.map((row, rowIndex) => rowIndex === index ? { ...row, quantity: event.target.value } : row);
                    setDraft({ ...draft, items });
                  }} />
                  <input className={inputClass} type="number" min="0" step="0.01" placeholder="Unit cost" aria-label="Unit cost" value={item.unit_cost} onChange={(event) => {
                    const items = draft.items.map((row, rowIndex) => rowIndex === index ? { ...row, unit_cost: event.target.value } : row);
                    setDraft({ ...draft, items });
                  }} />
                </div>
              ))}
            </div>
            <button className={`${btnPrimary} mt-3`}>Save draft</button>
          </form>
          <div className="space-y-3">
            {orders.map((order) => (
              <article key={order.order_id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{order.code} · {order.supplier_name}</h3>
                    <p className="text-sm text-slate-500">{titleCase(order.status)} · {formatMoney(order.total_cost, user.currency)} · expected {formatDate(order.expected_delivery)}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {user.permissions?.approve_orders && order.status === "draft" ? <button className={btnPrimary} onClick={() => setStatus(order, "approved")}>Approve</button> : null}
                    {user.permissions?.approve_orders && order.status === "approved" ? <button className={btnSecondary} onClick={() => setStatus(order, "ordered")}>Mark ordered</button> : null}
                    {["approved", "ordered", "partially_received"].includes(order.status) ? <button className={btnSecondary} onClick={() => setReceiveOrder({ ...order, items: order.items.map((item) => ({ ...item, receive_now: item.remaining_quantity })) })}>Receive</button> : null}
                    {user.permissions?.approve_orders && ["draft", "approved", "ordered"].includes(order.status) ? <button className="text-sm text-red-700" onClick={() => setStatus(order, "cancelled")}>Cancel</button> : null}
                  </div>
                </div>
                <ul className="mt-3 text-sm text-slate-600">
                  {order.items.map((item) => (
                    <li key={item.id}>{item.product_name}: ordered {formatQty(item.quantity, item.unit)}, received {formatQty(item.received_quantity, item.unit)}</li>
                  ))}
                </ul>
              </article>
            ))}
            {!orders.length ? <p className="text-sm text-slate-500">No purchase orders yet.</p> : null}
          </div>
        </div>
      ) : null}

      <Modal open={Boolean(receiveOrder)} title={receiveOrder ? `Receive ${receiveOrder.code}` : ""} onClose={() => setReceiveOrder(null)}>
        {receiveOrder ? (
          <form onSubmit={receive} className="space-y-3">
            {receiveOrder.items.map((item, index) => (
              <label key={item.id} className="block text-sm">
                <span className={labelClass}>{item.product_name} · remaining {formatQty(item.remaining_quantity, item.unit)}</span>
                <input className={inputClass} type="number" min="0" step="any" value={item.receive_now} onChange={(event) => {
                  const items = receiveOrder.items.map((row, rowIndex) => rowIndex === index ? { ...row, receive_now: event.target.value } : row);
                  setReceiveOrder({ ...receiveOrder, items });
                }} />
              </label>
            ))}
            <button className={btnPrimary}>Record delivery</button>
          </form>
        ) : null}
      </Modal>
    </div>
  );
}

function PlanColumn({ title, plan, currency }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-500">Spend {formatMoney(plan.total_cost, currency)} · left {formatMoney(plan.remaining, currency)} · score {plan.total_value}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{plan.explanation}</p>
      {plan.time_complexity ? <p className="mt-1 text-xs text-slate-500">{plan.time_complexity}. States computed: {plan.states_computed}.</p> : null}
      <h4 className="mt-3 text-sm font-medium">Selected</h4>
      <ul className="mt-1 space-y-1 text-sm">
        {plan.selected.length ? plan.selected.map((item) => (
          <li key={item.product_id}>{item.name} · {formatQty(item.suggested_quantity, item.unit)} · {formatMoney(item.cost, currency)}</li>
        )) : <li className="text-slate-500">Nothing selected.</li>}
      </ul>
      <h4 className="mt-3 text-sm font-medium">Not selected</h4>
      <ul className="mt-1 max-h-40 space-y-1 overflow-auto text-sm text-slate-600">
        {plan.excluded.slice(0, 8).map((item) => (
          <li key={`${item.product_id}-${item.reason}`}>{item.name}: {item.reason}</li>
        ))}
      </ul>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-900">{value}</dd>
    </div>
  );
}

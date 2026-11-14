import { useEffect, useState } from "react";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import UrgencyBadge from "../components/UrgencyBadge";
import Spinner from "../components/Spinner";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";
import { formatDateTime, formatDays, formatMoney, formatQty, titleCase } from "../utils/format";

export default function Simulations() {
  const { user } = useAuth();
  const toast = useToast();
  const [mode, setMode] = useState("demand");
  const [products, setProducts] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [demand, setDemand] = useState({ product_ids: [], all_products: false, increase_percent: 30, duration_days: 14 });
  const [delay, setDelay] = useState({ supplier_id: "", extra_days: 3 });
  const [budget, setBudget] = useState({ original_budget: user.restock_budget || 10000, reduced_budget: 6000 });

  async function loadHistory() {
    const response = await api.get("/simulations/history");
    setHistory(response.data.data);
  }

  useEffect(() => {
    Promise.all([
      api.get("/products", { params: { per_page: 100, sort: "name" } }),
      api.get("/suppliers"),
      api.get("/simulations/history"),
    ]).then(([productResponse, supplierResponse, historyResponse]) => {
      setProducts(productResponse.data.data);
      setSuppliers(supplierResponse.data.data);
      setHistory(historyResponse.data.data);
    }).catch((err) => toast.push(errorMessage(err), "error"));
  }, []);

  async function run(path, payload) {
    setLoading(true);
    try {
      const response = await api.post(path, payload);
      setResult(response.data.data);
      toast.push("Simulation saved. Live inventory was not changed.");
      loadHistory();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  }

  function toggleProduct(id) {
    setDemand((current) => ({
      ...current,
      product_ids: current.product_ids.includes(id)
        ? current.product_ids.filter((value) => value !== id)
        : [...current.product_ids, id],
    }));
  }

  return (
    <div>
      <PageHeader title="Simulations" subtitle="These scenarios use a temporary copy of the current metrics. They do not change stock or create orders." />
      <div className="mb-4 flex flex-wrap gap-2">
        {[["demand", "Demand spike"], ["delay", "Supplier delay"], ["budget", "Budget change"], ["history", "History"]].map(([id, label]) => (
          <button key={id} type="button" className={`rounded-full px-3 py-1.5 text-sm ${mode === id ? "bg-navy-900 text-white" : "bg-white ring-1 ring-slate-200"}`} onClick={() => setMode(id)}>{label}</button>
        ))}
      </div>

      {mode === "demand" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-600">What happens if demand increases by a chosen percent?</p>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <label><span className={labelClass}>Increase %</span><input className={inputClass} type="number" min="1" max="500" value={demand.increase_percent} onChange={(event) => setDemand({ ...demand, increase_percent: event.target.value })} /></label>
            <label><span className={labelClass}>Duration (days)</span><input className={inputClass} type="number" min="1" max="90" value={demand.duration_days} onChange={(event) => setDemand({ ...demand, duration_days: event.target.value })} /></label>
            <label className="flex items-end gap-2 text-sm"><input type="checkbox" checked={demand.all_products} onChange={(event) => setDemand({ ...demand, all_products: event.target.checked })} /> All products</label>
          </div>
          {demand.all_products ? null : (
            <div className="mt-3 grid max-h-48 gap-2 overflow-auto sm:grid-cols-2">
              {products.map((product) => (
                <label key={product.product_id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={demand.product_ids.includes(product.product_id)} onChange={() => toggleProduct(product.product_id)} />
                  {product.name}
                </label>
              ))}
            </div>
          )}
          <button className={`${btnPrimary} mt-4`} disabled={loading} onClick={() => run("/simulations/demand-spike", demand)}>Run demand simulation</button>
        </section>
      ) : null}

      {mode === "delay" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-600">What happens if one supplier is late?</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label><span className={labelClass}>Supplier</span>
              <select className={inputClass} value={delay.supplier_id} onChange={(event) => setDelay({ ...delay, supplier_id: event.target.value })}>
                <option value="">Select</option>
                {suppliers.map((supplier) => <option key={supplier.supplier_id} value={supplier.supplier_id}>{supplier.name}</option>)}
              </select>
            </label>
            <label><span className={labelClass}>Extra days</span><input className={inputClass} type="number" min="1" value={delay.extra_days} onChange={(event) => setDelay({ ...delay, extra_days: event.target.value })} /></label>
          </div>
          <button className={`${btnPrimary} mt-4`} disabled={loading} onClick={() => run("/simulations/supplier-delay", { ...delay, supplier_id: Number(delay.supplier_id) })}>Run delay simulation</button>
        </section>
      ) : null}

      {mode === "budget" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-600">Compare the greedy plan and the dynamic program at two budgets.</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label><span className={labelClass}>Original budget</span><input className={inputClass} type="number" min="0" value={budget.original_budget} onChange={(event) => setBudget({ ...budget, original_budget: event.target.value })} /></label>
            <label><span className={labelClass}>Simulated budget</span><input className={inputClass} type="number" min="0" value={budget.reduced_budget} onChange={(event) => setBudget({ ...budget, reduced_budget: event.target.value })} /></label>
          </div>
          <button className={`${btnPrimary} mt-4`} disabled={loading} onClick={() => run("/simulations/budget-reduction", budget)}>Compare budgets</button>
        </section>
      ) : null}

      {mode === "history" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          {history.length ? history.map((row) => (
            <div key={row.simulation_id} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 py-3">
              <div>
                <p className="font-medium">{titleCase(row.scenario_type)}</p>
                <p className="text-sm text-slate-500">{row.summary}</p>
                <p className="text-xs text-slate-400">{formatDateTime(row.created_at)}</p>
              </div>
              <div className="flex gap-2">
                <button className={btnSecondary} onClick={() => setResult(row.results)}>View</button>
                <button className={btnPrimary} onClick={() => run(`/simulations/${row.simulation_id}/rerun`, {})}>Rerun</button>
              </div>
            </div>
          )) : <p className="text-sm text-slate-500">No simulations yet.</p>}
        </section>
      ) : null}

      {loading ? <div className="mt-4"><Spinner label="Running simulation" /></div> : null}
      {result ? <ResultCard result={result} currency={user.currency} /> : null}
    </div>
  );
}

function ResultCard({ result, currency }) {
  return (
    <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-semibold text-slate-900">{result.summary}</h2>
      <p className="mt-1 text-sm text-slate-500">{result.note}</p>
      {result.recommendations ? <p className="mt-2 text-sm text-slate-700">{result.recommendations}</p> : null}
      {result.comparisons ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Product</th><th>Before</th><th>After</th><th>Shortfall</th></tr></thead>
            <tbody>
              {result.comparisons.map((row) => (
                <tr key={row.product_id} className="border-t border-slate-100">
                  <td className="py-2 font-medium">{row.name}</td>
                  <td><UrgencyBadge urgency={row.before.urgency} /> {formatDays(row.before.days_until_stockout)}</td>
                  <td><UrgencyBadge urgency={row.after.urgency} /> {formatDays(row.after.days_until_stockout)}</td>
                  <td>{row.shortfall == null ? "—" : formatQty(row.shortfall, row.unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {result.differences ? (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="font-medium">Dropped under the simulated budget</h3>
            <ul className="mt-2 text-sm">{result.differences.excluded_under_simulated_budget.map((item) => <li key={item.product_id}>{item.name} · {formatMoney(item.cost, currency)}</li>)}</ul>
          </div>
          <div>
            <h3 className="font-medium">Original optimal spend</h3>
            <p className="text-sm">{formatMoney(result.original?.dynamic_programming?.total_cost, currency)} → {formatMoney(result.simulated?.dynamic_programming?.total_cost, currency)}</p>
          </div>
        </div>
      ) : null}
    </section>
  );
}

import { useEffect, useState } from "react";
import api, { errorMessage } from "../services/api";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import Pagination from "../components/Pagination";
import Spinner from "../components/Spinner";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";
import { formatDateTime, formatMoney, formatQty, titleCase } from "../utils/format";
import { useAuth } from "../context/AuthContext";

const TYPES = [
  { id: "sale", label: "Sale" },
  { id: "consumption", label: "Consumption" },
  { id: "wastage", label: "Wastage" },
  { id: "adjustment", label: "Adjustment" },
];

export default function SalesUsage() {
  const { user } = useAuth();
  const toast = useToast();
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({ transaction_type: "sale", product_id: "", quantity: "", unit_price: "", reason: "", notes: "", transaction_date: "" });
  const [filters, setFilters] = useState({ type: "", product_id: "", from: "", to: "", page: 1 });
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load(next = filters) {
    setLoading(true);
    try {
      const [history, summaryResponse, productResponse] = await Promise.all([
        api.get("/transactions", { params: { ...next, per_page: 12 } }),
        api.get("/transactions/summary", { params: { from: next.from, to: next.to } }),
        api.get("/products", { params: { per_page: 100, sort: "name" } }),
      ]);
      setRows(history.data.data);
      setMeta(history.data.meta);
      setSummary(summaryResponse.data.data);
      setProducts(productResponse.data.data);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(filters); }, []);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.post("/transactions", {
        ...form,
        product_id: Number(form.product_id),
        unit_price: form.transaction_type === "sale" ? form.unit_price || undefined : undefined,
        transaction_date: form.transaction_date || undefined,
      });
      toast.push("Movement recorded and stock updated.");
      setForm({ ...form, quantity: "", reason: "", notes: "" });
      load(filters);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setSaving(false);
    }
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await api.post("/transactions/import", body);
      toast.push(`Imported ${response.data.data.imported} rows in file order.`);
      load(filters);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      event.target.value = "";
    }
  }

  async function downloadTemplate() {
    const response = await api.get("/transactions/template", { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "stockwise-sales-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader title="Sales and usage" subtitle="Record what left the shelf. Stock and the restock ranking update together." />
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Sales revenue</p>
          <p className="mt-1 text-xl font-semibold">{formatMoney(summary?.sales_revenue, user.currency)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Sales count</p>
          <p className="mt-1 text-xl font-semibold">{summary?.by_type?.sale?.count || 0}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Wastage entries</p>
          <p className="mt-1 text-xl font-semibold">{summary?.by_type?.wastage?.count || 0}</p>
        </div>
      </div>
      <form onSubmit={submit} className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap gap-2">
          {TYPES.map((type) => (
            <button key={type.id} type="button" onClick={() => setForm({ ...form, transaction_type: type.id })} className={`rounded-full px-3 py-1 text-sm ${form.transaction_type === type.id ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-700"}`}>
              {type.label}
            </button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <label><span className={labelClass}>Product</span>
            <select className={inputClass} required value={form.product_id} onChange={(event) => setForm({ ...form, product_id: event.target.value })}>
              <option value="">Select</option>
              {products.map((product) => <option key={product.product_id} value={product.product_id}>{product.name}</option>)}
            </select>
          </label>
          <label><span className={labelClass}>{form.transaction_type === "adjustment" ? "Quantity change (+/-)" : "Quantity"}</span>
            <input className={inputClass} type="number" step="any" required value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
          </label>
          {form.transaction_type === "sale" ? (
            <label><span className={labelClass}>Unit selling price</span>
              <input className={inputClass} type="number" min="0" step="0.01" placeholder="Product price if blank" value={form.unit_price} onChange={(event) => setForm({ ...form, unit_price: event.target.value })} />
            </label>
          ) : null}
          <label><span className={labelClass}>Date</span>
            <input className={inputClass} type="date" value={form.transaction_date} onChange={(event) => setForm({ ...form, transaction_date: event.target.value })} />
          </label>
          <label className="md:col-span-2"><span className={labelClass}>Reason {form.transaction_type === "wastage" || form.transaction_type === "adjustment" ? "(required)" : ""}</span>
            <input className={inputClass} value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
          </label>
          <label className="md:col-span-3"><span className={labelClass}>Notes</span>
            <input className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button className={btnPrimary} disabled={saving}>{saving ? "Saving..." : "Record movement"}</button>
          <label className={btnSecondary}>
            Import CSV
            <input type="file" accept=".csv,text/csv" className="hidden" onChange={upload} />
          </label>
          <button type="button" className={btnSecondary} onClick={downloadTemplate}>Download template</button>
        </div>
      </form>
      <div className="mb-3 grid gap-3 md:grid-cols-4">
        <select className={inputClass} aria-label="Filter by type" value={filters.type} onChange={(event) => { const next = { ...filters, type: event.target.value, page: 1 }; setFilters(next); load(next); }}>
          <option value="">All types</option>
          {TYPES.map((type) => <option key={type.id} value={type.id}>{type.label}</option>)}
          <option value="receipt">Receipt</option>
          <option value="opening">Opening</option>
        </select>
        <select className={inputClass} aria-label="Filter by product" value={filters.product_id} onChange={(event) => { const next = { ...filters, product_id: event.target.value, page: 1 }; setFilters(next); load(next); }}>
          <option value="">All products</option>
          {products.map((product) => <option key={product.product_id} value={product.product_id}>{product.name}</option>)}
        </select>
        <input className={inputClass} type="date" aria-label="From" value={filters.from} onChange={(event) => { const next = { ...filters, from: event.target.value, page: 1 }; setFilters(next); load(next); }} />
        <input className={inputClass} type="date" aria-label="To" value={filters.to} onChange={(event) => { const next = { ...filters, to: event.target.value, page: 1 }; setFilters(next); load(next); }} />
      </div>
      {loading ? <Spinner /> : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <DataTable
            columns={[
              { key: "transaction_date", label: "When", render: (row) => formatDateTime(row.transaction_date) },
              { key: "product_name", label: "Product" },
              { key: "transaction_type", label: "Type", render: (row) => titleCase(row.transaction_type) },
              { key: "signed_quantity", label: "Quantity", render: (row) => formatQty(row.signed_quantity, row.unit) },
              { key: "unit_price", label: "Price", render: (row) => row.unit_price ? formatMoney(row.unit_price, user.currency) : "—" },
              { key: "stock_after", label: "Stock after", render: (row) => formatQty(row.stock_after, row.unit) },
              { key: "reason", label: "Reason", render: (row) => row.reason || "—" },
            ]}
            rows={rows}
            rowKey="transaction_id"
            emptyTitle="No movements in this filter"
          />
          <Pagination meta={meta} onPage={(page) => { const next = { ...filters, page }; setFilters(next); load(next); }} />
        </div>
      )}
    </div>
  );
}

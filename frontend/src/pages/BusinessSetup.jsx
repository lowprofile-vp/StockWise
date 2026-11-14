import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";

const BLANK = { name: "", category: "General", current_stock: "", minimum_stock: "", unit: "kg", selling_price: "", purchase_price: "" };

export default function BusinessSetup() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    business_name: user?.business_name || "",
    business_type: "Grocery",
    currency: "INR",
    restock_budget: "10000",
    categories: "General, Grocery",
  });
  const [products, setProducts] = useState([{ ...BLANK }]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateProduct(index, field, value) {
    setProducts((rows) => rows.map((row, rowIndex) => (rowIndex === index ? { ...row, [field]: value } : row)));
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.post("/business/setup", {
        ...form,
        categories: form.categories.split(",").map((item) => item.trim()).filter(Boolean),
        products: products.filter((row) => row.name.trim()).map((row) => ({
          ...row,
          current_stock: row.current_stock || 0,
          minimum_stock: row.minimum_stock || 0,
          selling_price: row.selling_price || 0,
          purchase_price: row.purchase_price || 0,
        })),
      });
      await refresh();
      navigate("/overview");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-8">
      <form onSubmit={submit} className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold text-teal-800">StockWise</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Set up {user?.business_name || "your workspace"}</h1>
        <p className="mt-1 text-sm text-slate-500">Currency defaults to INR. You can add products now or leave them for the inventory page.</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label><span className={labelClass}>Business name</span><input className={inputClass} required value={form.business_name} onChange={(event) => setForm({ ...form, business_name: event.target.value })} /></label>
          <label>
            <span className={labelClass}>Business type</span>
            <select className={inputClass} value={form.business_type} onChange={(event) => setForm({ ...form, business_type: event.target.value })}>
              {["Grocery", "College Canteen", "Retail", "Restaurant", "Other"].map((type) => <option key={type}>{type}</option>)}
            </select>
          </label>
          <label><span className={labelClass}>Currency</span><input className={inputClass} maxLength={3} value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} /></label>
          <label><span className={labelClass}>Initial restocking budget</span><input className={inputClass} type="number" min="0" step="1" value={form.restock_budget} onChange={(event) => setForm({ ...form, restock_budget: event.target.value })} /></label>
          <label className="sm:col-span-2"><span className={labelClass}>Categories, separated by commas</span><input className={inputClass} value={form.categories} onChange={(event) => setForm({ ...form, categories: event.target.value })} /></label>
        </div>
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Opening inventory</h2>
            <button type="button" className={btnSecondary} onClick={() => setProducts((rows) => [...rows, { ...BLANK }])}>Add row</button>
          </div>
          <div className="space-y-3">
            {products.map((product, index) => (
              <div key={index} className="grid gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-3">
                <input className={inputClass} placeholder="Name" aria-label="Product name" value={product.name} onChange={(event) => updateProduct(index, "name", event.target.value)} />
                <input className={inputClass} placeholder="Category" aria-label="Category" value={product.category} onChange={(event) => updateProduct(index, "category", event.target.value)} />
                <input className={inputClass} placeholder="Unit" aria-label="Unit" value={product.unit} onChange={(event) => updateProduct(index, "unit", event.target.value)} />
                <input className={inputClass} type="number" min="0" step="any" placeholder="Quantity" aria-label="Quantity" value={product.current_stock} onChange={(event) => updateProduct(index, "current_stock", event.target.value)} />
                <input className={inputClass} type="number" min="0" step="any" placeholder="Minimum" aria-label="Minimum" value={product.minimum_stock} onChange={(event) => updateProduct(index, "minimum_stock", event.target.value)} />
                <input className={inputClass} type="number" min="0" step="0.01" placeholder="Purchase price" aria-label="Purchase price" value={product.purchase_price} onChange={(event) => updateProduct(index, "purchase_price", event.target.value)} />
              </div>
            ))}
          </div>
        </div>
        {error ? <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <button className={`${btnPrimary} mt-6`} disabled={loading}>{loading ? "Saving..." : "Finish setup"}</button>
      </form>
    </div>
  );
}

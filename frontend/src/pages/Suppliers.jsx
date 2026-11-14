import { useEffect, useState } from "react";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import Spinner from "../components/Spinner";
import ConfirmDialog from "../components/ConfirmDialog";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";
import { formatDate, formatMoney, titleCase } from "../utils/format";

const EMPTY = { name: "", contact_person: "", phone: "", email: "", address: "", delivery_days: 3, notes: "" };

export default function Suppliers() {
  const { user } = useAuth();
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(null);
  const [detail, setDetail] = useState(null);
  const [compareId, setCompareId] = useState("");
  const [comparison, setComparison] = useState(null);
  const [deactivate, setDeactivate] = useState(null);
  const canManage = user.permissions?.manage_suppliers;

  async function load(term = search) {
    setLoading(true);
    try {
      const [supplierResponse, productResponse] = await Promise.all([
        api.get("/suppliers", { params: { search: term, include_inactive: true } }),
        api.get("/products", { params: { per_page: 100, sort: "name" } }),
      ]);
      setRows(supplierResponse.data.data);
      setProducts(productResponse.data.data);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(""); }, []);

  async function save(event) {
    event.preventDefault();
    try {
      if (form.supplier_id) await api.put(`/suppliers/${form.supplier_id}`, form);
      else await api.post("/suppliers", form);
      toast.push("Supplier saved.");
      setForm(null);
      load(search);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function openDetail(row) {
    const response = await api.get(`/suppliers/${row.supplier_id}`);
    setDetail(response.data.data);
  }

  async function compare(productId) {
    setCompareId(productId);
    if (!productId) {
      setComparison(null);
      return;
    }
    const response = await api.get("/suppliers/compare", { params: { product_id: productId } });
    setComparison(response.data.data);
  }

  async function link(supplierId, productId) {
    try {
      await api.post(`/suppliers/${supplierId}/products`, { product_id: Number(productId), purchase_price: products.find((item) => item.product_id === Number(productId))?.purchase_price || 0 });
      toast.push("Product linked.");
      openDetail({ supplier_id: supplierId });
      load(search);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  return (
    <div>
      <PageHeader
        title="Suppliers"
        subtitle="Lead time and purchase price on these links drive the restock recommendation."
        actions={canManage ? <button className={btnPrimary} onClick={() => setForm({ ...EMPTY })}>Add supplier</button> : null}
      />
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <input className={inputClass} placeholder="Search suppliers" aria-label="Search suppliers" value={search} onChange={(event) => { setSearch(event.target.value); load(event.target.value); }} />
        <select className={inputClass} aria-label="Compare prices for a product" value={compareId} onChange={(event) => compare(event.target.value)}>
          <option value="">Compare supplier prices for a product</option>
          {products.map((product) => <option key={product.product_id} value={product.product_id}>{product.name}</option>)}
        </select>
      </div>
      {comparison ? (
        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-semibold">{comparison.name}</h2>
          {comparison.suppliers.length ? (
            <ul className="mt-2 space-y-1 text-sm">
              {comparison.suppliers.map((supplier) => (
                <li key={supplier.supplier_id}>{supplier.name}: {formatMoney(supplier.purchase_price, user.currency)} · {supplier.delivery_days} days {supplier.is_preferred ? "· preferred" : ""}</li>
              ))}
            </ul>
          ) : <p className="mt-2 text-sm text-slate-500">No suppliers are linked to this product yet.</p>}
        </div>
      ) : null}
      {loading ? <Spinner /> : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <DataTable
            columns={[
              { key: "supplier_id", label: "Supplier ID" },
              { key: "name", label: "Name" },
              { key: "contact_person", label: "Contact", render: (row) => row.contact_person || "—" },
              { key: "phone", label: "Phone", render: (row) => row.phone || "—" },
              { key: "email", label: "Email", render: (row) => row.email || "—" },
              { key: "delivery_days", label: "Lead time", render: (row) => `${row.delivery_days} days` },
              { key: "products", label: "Products", render: (row) => row.products.map((product) => product.name).join(", ") || "—" },
              { key: "is_active", label: "Status", render: (row) => (row.is_active ? "Active" : "Inactive") },
              { key: "actions", label: "Actions", render: (row) => (
                <div className="flex gap-2">
                  <button type="button" className="text-teal-800" onClick={(event) => { event.stopPropagation(); openDetail(row); }}>View</button>
                  {canManage ? <button type="button" className="text-slate-700" onClick={(event) => { event.stopPropagation(); setForm(row); }}>Edit</button> : null}
                  {canManage && row.is_active ? <button type="button" className="text-red-700" onClick={(event) => { event.stopPropagation(); setDeactivate(row); }}>Deactivate</button> : null}
                </div>
              ) },
            ]}
            rows={rows}
            rowKey="supplier_id"
            onRow={openDetail}
            emptyTitle="No suppliers yet"
          />
        </div>
      )}
      <Modal open={Boolean(form)} title={form?.supplier_id ? "Edit supplier" : "Add supplier"} onClose={() => setForm(null)}>
        {form ? (
          <form onSubmit={save} className="grid gap-3">
            {["name", "contact_person", "phone", "email", "address", "notes"].map((field) => (
              <label key={field}>
                <span className={labelClass}>{titleCase(field)}</span>
                <input className={inputClass} required={field === "name"} value={form[field] || ""} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />
              </label>
            ))}
            <label>
              <span className={labelClass}>Average delivery time (days)</span>
              <input className={inputClass} type="number" min="0" required value={form.delivery_days} onChange={(event) => setForm({ ...form, delivery_days: event.target.value })} />
            </label>
            <button className={btnPrimary}>Save supplier</button>
          </form>
        ) : null}
      </Modal>
      <Modal open={Boolean(detail)} title={detail?.name || "Supplier"} onClose={() => setDetail(null)} wide>
        {detail ? (
          <div className="space-y-3 text-sm">
            <p>{detail.address || "No address"} · {detail.phone || "No phone"} · {detail.email || "No email"}</p>
            <p>Promised lead time: {detail.delivery_days} days. On-time rate: {detail.performance?.on_time_rate ?? "—"}%. Average delay: {detail.performance?.average_delay_days ?? "—"} days.</p>
            <h3 className="font-semibold">Products supplied</h3>
            <ul>{detail.products.map((product) => <li key={product.product_id}>{product.name} · {formatMoney(product.purchase_price, user.currency)} · MOQ {product.minimum_order_quantity}</li>)}</ul>
            {canManage ? (
              <label className="block">
                <span className={labelClass}>Link another product</span>
                <select className={inputClass} defaultValue="" onChange={(event) => event.target.value && link(detail.supplier_id, event.target.value)}>
                  <option value="">Choose a product</option>
                  {products.map((product) => <option key={product.product_id} value={product.product_id}>{product.name}</option>)}
                </select>
              </label>
            ) : null}
            <h3 className="font-semibold">Order history</h3>
            <ul>{detail.orders?.map((order) => <li key={order.order_id}>{order.code} · {titleCase(order.status)} · {formatMoney(order.total_cost, user.currency)} · {formatDate(order.created_at)}</li>)}</ul>
            <button type="button" className={btnSecondary} onClick={() => setDetail(null)}>Close</button>
          </div>
        ) : null}
      </Modal>
      <ConfirmDialog
        open={Boolean(deactivate)}
        title="Deactivate supplier"
        message={deactivate ? `${deactivate.name} will no longer be offered for new recommendations.` : ""}
        confirmLabel="Deactivate"
        onClose={() => setDeactivate(null)}
        onConfirm={async () => {
          await api.delete(`/suppliers/${deactivate.supplier_id}`);
          setDeactivate(null);
          load(search);
        }}
      />
    </div>
  );
}

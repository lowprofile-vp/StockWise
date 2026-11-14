import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import Pagination from "../components/Pagination";
import StockBadge from "../components/StockBadge";
import UrgencyBadge from "../components/UrgencyBadge";
import Modal from "../components/Modal";
import ProductForm from "../components/ProductForm";
import ConfirmDialog from "../components/ConfirmDialog";
import Spinner from "../components/Spinner";
import { btnPrimary, inputClass } from "../utils/styles";
import { formatMoney, formatQty } from "../utils/format";

export default function Inventory() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState(null);
  const [filters, setFilters] = useState({ search: "", category: "", status: "", sort: "name", order: "asc", page: 1 });
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const canManage = user.permissions?.manage_products;

  async function load(next = filters) {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/products", { params: { ...next, per_page: 10 } });
      setRows(response.data.data);
      setMeta(response.data.meta);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(filters);
    api.get("/categories").then((response) => setCategories(response.data.data)).catch(() => {});
    api.get("/suppliers").then((response) => setSuppliers(response.data.data)).catch(() => {});
  }, []);

  function apply(partial) {
    const next = { ...filters, ...partial, page: partial.page || 1 };
    setFilters(next);
    load(next);
  }

  async function save(payload) {
    setSaving(true);
    try {
      if (editing) await api.put(`/products/${editing.product_id}`, payload);
      else await api.post("/products", payload);
      toast.push(editing ? "Product updated." : "Product added.");
      setFormOpen(false);
      setEditing(null);
      load(filters);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    } finally {
      setSaving(false);
    }
  }

  async function deactivate() {
    try {
      await api.delete(`/products/${pendingDelete.product_id}`);
      toast.push(`${pendingDelete.name} was deactivated.`);
      setPendingDelete(null);
      load(filters);
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  const columns = [
    { key: "code", label: "Product ID" },
    { key: "name", label: "Name" },
    { key: "category", label: "Category" },
    { key: "current_stock", label: "Quantity", render: (row) => formatQty(row.current_stock, row.unit) },
    { key: "minimum_stock", label: "Minimum", render: (row) => formatQty(row.minimum_stock, row.unit) },
    { key: "unit", label: "Unit" },
    { key: "selling_price", label: "Selling price", render: (row) => formatMoney(row.selling_price, user.currency) },
    { key: "purchase_price", label: "Purchase price", render: (row) => formatMoney(row.purchase_price, user.currency) },
    { key: "supplier_name", label: "Supplier", render: (row) => row.supplier_name || "—" },
    { key: "stock_status", label: "Status", render: (row) => <StockBadge status={row.stock_status} /> },
    { key: "urgency", label: "Urgency", render: (row) => <UrgencyBadge urgency={row.urgency} /> },
    {
      key: "actions",
      label: "Actions",
      render: (row) => (
        <div className="flex gap-2">
          <button type="button" className="text-teal-800" onClick={(event) => { event.stopPropagation(); navigate(`/inventory/${row.product_id}`); }}>View</button>
          {canManage ? (
            <>
              <button type="button" className="text-slate-700" onClick={(event) => { event.stopPropagation(); setEditing(row); setFormOpen(true); }}>Edit</button>
              <button type="button" className="text-red-700" onClick={(event) => { event.stopPropagation(); setPendingDelete(row); }}>Deactivate</button>
            </>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="Search, filter, and open a product to see movement, demand, and the suggested reorder."
        actions={canManage ? <button className={btnPrimary} onClick={() => { setEditing(null); setFormOpen(true); }}>Add product</button> : null}
      />
      <div className="mb-4 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-4">
        <input className={inputClass} placeholder="Search name or SW-0001" aria-label="Search products" value={filters.search} onChange={(event) => apply({ search: event.target.value })} />
        <select className={inputClass} aria-label="Filter by category" value={filters.category} onChange={(event) => apply({ category: event.target.value })}>
          <option value="">All categories</option>
          {categories.map((category) => <option key={category.id} value={category.name}>{category.name}</option>)}
        </select>
        <select className={inputClass} aria-label="Filter by stock status" value={filters.status} onChange={(event) => apply({ status: event.target.value })}>
          <option value="">All statuses</option>
          {["Healthy", "Low Stock", "Critical", "Out of Stock"].map((status) => <option key={status}>{status}</option>)}
        </select>
        <select className={inputClass} aria-label="Sort products" value={`${filters.sort}:${filters.order}`} onChange={(event) => {
          const [sort, order] = event.target.value.split(":");
          apply({ sort, order });
        }}>
          <option value="name:asc">Name A–Z</option>
          <option value="name:desc">Name Z–A</option>
          <option value="quantity:asc">Quantity low to high</option>
          <option value="quantity:desc">Quantity high to low</option>
          <option value="price:asc">Price low to high</option>
          <option value="price:desc">Price high to low</option>
          <option value="urgency:desc">Urgency first</option>
        </select>
      </div>
      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <Spinner label="Loading inventory" /> : (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <DataTable columns={columns} rows={rows} rowKey="product_id" onRow={(row) => navigate(`/inventory/${row.product_id}`)} emptyTitle="No products match these filters" />
          <Pagination meta={meta} onPage={(page) => apply({ page })} />
        </div>
      )}
      <Modal open={formOpen} title={editing ? "Edit product" : "Add product"} onClose={() => setFormOpen(false)} wide>
        <ProductForm initial={editing} categories={categories} suppliers={suppliers} submitting={saving} onCancel={() => setFormOpen(false)} onSubmit={save} />
      </Modal>
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Deactivate product"
        message={pendingDelete ? `${pendingDelete.name} will leave the active catalog. Past sales and orders stay in the history.` : ""}
        confirmLabel="Deactivate"
        onClose={() => setPendingDelete(null)}
        onConfirm={deactivate}
      />
    </div>
  );
}

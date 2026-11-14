import { useEffect, useState } from "react";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";

const EMPTY = {
  name: "",
  category: "",
  current_stock: "",
  minimum_stock: "",
  unit: "kg",
  selling_price: "",
  purchase_price: "",
  preferred_supplier_id: "",
  notes: "",
};

export default function ProductForm({ initial, categories, suppliers, onSubmit, onCancel, submitting }) {
  const [form, setForm] = useState(EMPTY);
  const editing = Boolean(initial?.product_id);

  useEffect(() => {
    if (!initial) {
      setForm(EMPTY);
      return;
    }
    setForm({
      name: initial.name || "",
      category: initial.category || "",
      current_stock: initial.current_stock ?? "",
      minimum_stock: initial.minimum_stock ?? "",
      unit: initial.unit || "kg",
      selling_price: initial.selling_price ?? "",
      purchase_price: initial.purchase_price ?? "",
      preferred_supplier_id: initial.supplier_id || "",
      notes: initial.notes || "",
    });
  }, [initial]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function submit(event) {
    event.preventDefault();
    const payload = {
      name: form.name,
      category: form.category,
      minimum_stock: form.minimum_stock || 0,
      unit: form.unit,
      selling_price: form.selling_price || 0,
      purchase_price: form.purchase_price || 0,
      notes: form.notes,
      preferred_supplier_id: form.preferred_supplier_id ? Number(form.preferred_supplier_id) : null,
    };
    if (!editing) payload.current_stock = form.current_stock || 0;
    if (form.preferred_supplier_id) {
      payload.supplier_links = [
        {
          supplier_id: Number(form.preferred_supplier_id),
          purchase_price: form.purchase_price || 0,
          minimum_order_quantity: 0,
        },
      ];
    }
    onSubmit(payload);
  }

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
      <label className="sm:col-span-2">
        <span className={labelClass}>Product name</span>
        <input className={inputClass} value={form.name} onChange={(event) => update("name", event.target.value)} required />
      </label>
      <label>
        <span className={labelClass}>Category</span>
        <select className={inputClass} value={form.category} onChange={(event) => update("category", event.target.value)} required>
          <option value="">Select a category</option>
          {categories.map((category) => (
            <option key={category.id || category.name} value={category.name}>
              {category.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className={labelClass}>Unit</span>
        <input className={inputClass} value={form.unit} onChange={(event) => update("unit", event.target.value)} required />
      </label>
      {editing ? null : (
        <label>
          <span className={labelClass}>Opening quantity</span>
          <input className={inputClass} type="number" min="0" step="any" value={form.current_stock} onChange={(event) => update("current_stock", event.target.value)} />
        </label>
      )}
      <label>
        <span className={labelClass}>Minimum stock</span>
        <input className={inputClass} type="number" min="0" step="any" value={form.minimum_stock} onChange={(event) => update("minimum_stock", event.target.value)} required />
      </label>
      <label>
        <span className={labelClass}>Selling price</span>
        <input className={inputClass} type="number" min="0" step="0.01" value={form.selling_price} onChange={(event) => update("selling_price", event.target.value)} required />
      </label>
      <label>
        <span className={labelClass}>Purchase price</span>
        <input className={inputClass} type="number" min="0" step="0.01" value={form.purchase_price} onChange={(event) => update("purchase_price", event.target.value)} required />
      </label>
      <label className="sm:col-span-2">
        <span className={labelClass}>Preferred supplier</span>
        <select className={inputClass} value={form.preferred_supplier_id} onChange={(event) => update("preferred_supplier_id", event.target.value)}>
          <option value="">No supplier yet</option>
          {suppliers.map((supplier) => (
            <option key={supplier.supplier_id} value={supplier.supplier_id}>
              {supplier.name} · {supplier.delivery_days} days
            </option>
          ))}
        </select>
      </label>
      <label className="sm:col-span-2">
        <span className={labelClass}>Notes</span>
        <textarea className={inputClass} rows="2" value={form.notes} onChange={(event) => update("notes", event.target.value)} />
      </label>
      <div className="flex justify-end gap-2 sm:col-span-2">
        <button type="button" className={btnSecondary} onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className={btnPrimary} disabled={submitting}>
          {submitting ? "Saving..." : editing ? "Save product" : "Add product"}
        </button>
      </div>
    </form>
  );
}

import { useEffect, useState } from "react";
import api, { errorMessage } from "../services/api";
import { supabaseEnabled } from "../services/supabase";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import PageHeader from "../components/PageHeader";
import { btnPrimary, btnSecondary, inputClass, labelClass } from "../utils/styles";

export default function Settings() {
  const { user, refresh, changePassword: savePassword } = useAuth();
  const toast = useToast();
  const [business, setBusiness] = useState(null);
  const [categories, setCategories] = useState([]);
  const [users, setUsers] = useState([]);
  const [categoryName, setCategoryName] = useState("");
  const [staff, setStaff] = useState({ name: "", email: "", password: "" });
  const [password, setPassword] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const owner = user.permissions?.manage_settings;

  async function load() {
    const [businessResponse, categoryResponse] = await Promise.all([
      api.get("/business"),
      api.get("/categories"),
    ]);
    setBusiness(businessResponse.data.data);
    setCategories(categoryResponse.data.data);
    if (owner) {
      const userResponse = await api.get("/users");
      setUsers(userResponse.data.data);
    }
  }

  useEffect(() => { load().catch((err) => toast.push(errorMessage(err), "error")); }, []);

  async function saveBusiness(event) {
    event.preventDefault();
    try {
      await api.put("/business", business);
      await refresh();
      toast.push("Business settings saved.");
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function addCategory(event) {
    event.preventDefault();
    try {
      await api.post("/categories", { name: categoryName });
      setCategoryName("");
      load();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function addStaff(event) {
    event.preventDefault();
    try {
      await api.post("/users", { ...staff, role: "staff" });
      setStaff({ name: "", email: "", password: "" });
      toast.push("Staff account created.");
      load();
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    try {
      await savePassword(password);
      setPassword({ current_password: "", new_password: "", confirm_password: "" });
      toast.push("Password updated.");
    } catch (err) {
      toast.push(errorMessage(err), "error");
    }
  }

  if (!business) return null;

  return (
    <div className="space-y-6">
      <PageHeader title="Business settings" subtitle="Workspace details, categories, staff, and your password." />
      <form onSubmit={saveBusiness} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-semibold">Workspace</h2>
        {owner ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label><span className={labelClass}>Business name</span><input className={inputClass} value={business.business_name} onChange={(event) => setBusiness({ ...business, business_name: event.target.value })} /></label>
            <label><span className={labelClass}>Type</span>
              <select className={inputClass} value={business.business_type} onChange={(event) => setBusiness({ ...business, business_type: event.target.value })}>
                {(business.business_types || []).map((type) => <option key={type}>{type}</option>)}
              </select>
            </label>
            <label><span className={labelClass}>Currency</span><input className={inputClass} value={business.currency} onChange={(event) => setBusiness({ ...business, currency: event.target.value.toUpperCase() })} /></label>
            <label><span className={labelClass}>Restocking budget</span><input className={inputClass} type="number" min="0" value={business.restock_budget} onChange={(event) => setBusiness({ ...business, restock_budget: event.target.value })} /></label>
            <p className="text-sm text-slate-600 md:col-span-2">Staff join with workspace code <span className="font-semibold">{business.join_code}</span>.</p>
            <button className={btnPrimary}>Save settings</button>
          </div>
        ) : <p className="mt-2 text-sm text-slate-600">{business.business_name} · {business.business_type} · {business.currency}. Only the owner can edit these.</p>}
      </form>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-semibold">Categories</h2>
        <ul className="mt-2 flex flex-wrap gap-2">
          {categories.map((category) => (
            <li key={category.id} className="rounded-full bg-slate-100 px-3 py-1 text-sm">
              {category.name}
              {owner ? <button type="button" className="ml-2 text-red-700" onClick={async () => { try { await api.delete(`/categories/${category.id}`); load(); } catch (err) { toast.push(errorMessage(err), "error"); } }}>Remove</button> : null}
            </li>
          ))}
        </ul>
        {owner ? (
          <form onSubmit={addCategory} className="mt-3 flex gap-2">
            <input className={inputClass} placeholder="New category" aria-label="New category" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} />
            <button className={btnSecondary}>Add</button>
          </form>
        ) : null}
      </section>

      {owner ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-semibold">Users</h2>
          <ul className="mt-2 space-y-2 text-sm">
            {users.map((member) => (
              <li key={member.user_id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                <span>{member.name} · {member.email} · {member.role_label}</span>
                {member.role === "staff" ? (
                  <button type="button" className="text-red-700" onClick={async () => { await api.put(`/users/${member.user_id}`, { is_active: !member.is_active }); load(); }}>
                    {member.is_active ? "Deactivate" : "Restore"}
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          {supabaseEnabled ? (
            <p className="mt-4 text-sm text-slate-600">
              Staff choose their own password. They register and enter workspace code <span className="font-semibold">{business.join_code}</span>.
            </p>
          ) : (
            <form onSubmit={addStaff} className="mt-4 grid gap-3 md:grid-cols-4">
              <input className={inputClass} placeholder="Name" aria-label="Staff name" required value={staff.name} onChange={(event) => setStaff({ ...staff, name: event.target.value })} />
              <input className={inputClass} placeholder="Email" aria-label="Staff email" type="email" required value={staff.email} onChange={(event) => setStaff({ ...staff, email: event.target.value })} />
              <input className={inputClass} placeholder="Password" aria-label="Staff password" type="password" required value={staff.password} onChange={(event) => setStaff({ ...staff, password: event.target.value })} />
              <button className={btnPrimary}>Add staff</button>
            </form>
          )}
        </section>
      ) : null}

      <form onSubmit={changePassword} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-semibold">Change password</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <input className={inputClass} type="password" placeholder="Current password" aria-label="Current password" value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} />
          <input className={inputClass} type="password" placeholder="New password" aria-label="New password" value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} />
          <input className={inputClass} type="password" placeholder="Confirm password" aria-label="Confirm password" value={password.confirm_password} onChange={(event) => setPassword({ ...password, confirm_password: event.target.value })} />
        </div>
        <button className={`${btnPrimary} mt-3`}>Update password</button>
      </form>
    </div>
  );
}

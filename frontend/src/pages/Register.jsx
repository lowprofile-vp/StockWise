import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";
import { btnPrimary, inputClass, labelClass } from "../utils/styles";
import { AuthShell } from "./Login";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm_password: "",
    business_name: "",
    role: "admin",
    join_code: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to={user.setup_complete ? "/overview" : "/setup"} replace />;

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Password and confirmation do not match.");
      return;
    }
    setLoading(true);
    try {
      const account = await register(form);
      navigate(account.role === "admin" && !account.setup_complete ? "/setup" : "/overview");
    } catch (err) {
      setError(errorMessage(err, "Could not create the account."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Create an account" subtitle="Owners start a workspace. Staff join with a code.">
      <form onSubmit={submit} className="space-y-4">
        <label className="block"><span className={labelClass}>Full name</span><input className={inputClass} required value={form.name} onChange={(event) => update("name", event.target.value)} /></label>
        <label className="block"><span className={labelClass}>Email</span><input className={inputClass} type="email" required value={form.email} onChange={(event) => update("email", event.target.value)} /></label>
        <label className="block"><span className={labelClass}>Password</span><input className={inputClass} type="password" required value={form.password} onChange={(event) => update("password", event.target.value)} /></label>
        <label className="block"><span className={labelClass}>Confirm password</span><input className={inputClass} type="password" required value={form.confirm_password} onChange={(event) => update("confirm_password", event.target.value)} /></label>
        <label className="block">
          <span className={labelClass}>Role</span>
          <select className={inputClass} value={form.role} onChange={(event) => update("role", event.target.value)}>
            <option value="admin">Admin / Owner</option>
            <option value="staff">Staff / Inventory Manager</option>
          </select>
        </label>
        {form.role === "admin" ? (
          <label className="block"><span className={labelClass}>Business name</span><input className={inputClass} required value={form.business_name} onChange={(event) => update("business_name", event.target.value)} /></label>
        ) : (
          <label className="block"><span className={labelClass}>Workspace code</span><input className={inputClass} required value={form.join_code} onChange={(event) => update("join_code", event.target.value.toUpperCase())} /></label>
        )}
        {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <button className={`${btnPrimary} w-full`} disabled={loading}>{loading ? "Creating account..." : "Register"}</button>
      </form>
      <p className="mt-4 text-sm text-slate-500">Already registered? <Link className="font-medium text-teal-800" to="/login">Log in</Link></p>
    </AuthShell>
  );
}

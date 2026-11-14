import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";
import { supabaseEnabled } from "../services/supabase";
import { btnPrimary, inputClass, labelClass } from "../utils/styles";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", remember: true });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={user.setup_complete ? "/overview" : "/setup"} replace />;

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const account = await login(form.email, form.password, form.remember);
      navigate(account.setup_complete ? "/overview" : "/setup");
    } catch (err) {
      setError(errorMessage(err, "Could not log in."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Log in" subtitle="Open your StockWise workspace.">
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className={labelClass}>Email</span>
          <input className={inputClass} type="email" autoComplete="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </label>
        <label className="block">
          <span className={labelClass}>Password</span>
          <input className={inputClass} type="password" autoComplete="current-password" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
        </label>
        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2 text-slate-600">
            <input type="checkbox" checked={form.remember} onChange={(event) => setForm({ ...form, remember: event.target.checked })} />
            Remember me
          </label>
          <Link to="/forgot-password" className="font-medium text-teal-800 hover:underline">Forgot password</Link>
        </div>
        {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <button className={`${btnPrimary} w-full`} disabled={loading}>{loading ? "Signing in..." : "Log in"}</button>
      </form>
      <p className="mt-4 text-sm text-slate-500">New workspace? <Link className="font-medium text-teal-800" to="/register">Register</Link></p>
    </AuthShell>
  );
}

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden bg-navy-900 p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <p className="text-lg font-semibold">StockWise</p>
        <div>
          <h2 className="text-3xl font-semibold">Restock what will run out, not only what looks low.</h2>
          <p className="mt-3 max-w-md text-sm leading-6 text-slate-300">Demand, supplier lead time, and the purchasing budget decide the order. Nothing is purchased until an owner approves it.</p>
        </div>
        {supabaseEnabled ? null : <p className="text-xs text-slate-400">Demo owner: admin@stockwise.demo · Admin@12345</p>}
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <p className="text-sm font-semibold text-teal-800 lg:hidden">StockWise</p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

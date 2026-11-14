import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../services/api";
import { authError, supabase, supabaseEnabled } from "../services/supabase";
import { btnPrimary, inputClass, labelClass } from "../utils/styles";
import { AuthShell } from "./Login";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    setResetUrl("");
    try {
      if (supabaseEnabled) {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });
        if (error) throw authError(error);
        setMessage("If that email is registered, Supabase sent a reset link. Add this site URL to the Supabase redirect allow list.");
      } else {
        const response = await api.post("/auth/forgot-password", { email });
        setMessage(response.data.message);
        setResetUrl(response.data.dev_reset_url || "");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Reset password" subtitle="We create a short-lived reset link for the account.">
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className={labelClass}>Email</span>
          <input className={inputClass} type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p> : null}
        {resetUrl ? (
          <p className="text-sm text-slate-600">
            Email is not configured in this environment. Open the recovery link:{" "}
            <Link className="font-medium text-teal-800 break-all" to={resetUrl.replace(/^https?:\/\/[^/]+/, "")}>{resetUrl}</Link>
          </p>
        ) : null}
        <button className={`${btnPrimary} w-full`} disabled={loading}>{loading ? "Sending..." : "Create reset link"}</button>
      </form>
      <p className="mt-4 text-sm"><Link className="text-teal-800" to="/login">Back to login</Link></p>
    </AuthShell>
  );
}

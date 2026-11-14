import axios from "axios";
import { accessToken, supabase, supabaseEnabled } from "./supabase";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:5000/api",
});

api.interceptors.request.use(async (config) => {
  const token = await accessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "";
    const profileMissing = error.response?.data?.details?.code === "profile_required";
    if (status === 401 && !profileMissing && !url.includes("/auth/login") && !url.includes("/auth/register") && !url.includes("/auth/provision")) {
      localStorage.removeItem("stockwise_token");
      sessionStorage.removeItem("stockwise_token");
      if (supabaseEnabled && supabase) supabase.auth.signOut();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error, fallback = "Something went wrong. Please try again.") {
  const data = error?.response?.data;
  if (!data) return error?.message || fallback;
  if (Array.isArray(data.details?.rows) && data.details.rows.length) {
    const rows = data.details.rows.map((row) => `Row ${row.row}: ${row.error}`).join(" ");
    return `${data.error} ${rows}`;
  }
  return data.error || fallback;
}

export default api;

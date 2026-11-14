import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabaseEnabled = Boolean(url && anonKey);

const preference = { remember: true };

const authStorage = {
  getItem(key) {
    return localStorage.getItem(key) ?? sessionStorage.getItem(key);
  },
  setItem(key, value) {
    const keep = preference.remember ? localStorage : sessionStorage;
    const drop = preference.remember ? sessionStorage : localStorage;
    drop.removeItem(key);
    keep.setItem(key, value);
  },
  removeItem(key) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  },
};

export const supabase = supabaseEnabled
  ? createClient(url, anonKey, {
      auth: {
        storage: authStorage,
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

export function setRemember(remember) {
  preference.remember = Boolean(remember);
}

export async function accessToken() {
  if (!supabase) {
    return localStorage.getItem("stockwise_token") || sessionStorage.getItem("stockwise_token");
  }
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token || null;
}

export function authError(error) {
  const message = error?.message || "Authentication failed.";
  const wrapped = new Error(message);
  wrapped.response = { data: { error: message } };
  return wrapped;
}

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "../services/api";
import { authError, setRemember, supabase, supabaseEnabled } from "../services/supabase";

const AuthContext = createContext(null);

function storeToken(token, remember) {
  localStorage.removeItem("stockwise_token");
  sessionStorage.removeItem("stockwise_token");
  if (remember) localStorage.setItem("stockwise_token", token);
  else sessionStorage.setItem("stockwise_token", token);
}

async function loadProfile() {
  const response = await api.get("/auth/me");
  return response.data.user;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (supabaseEnabled) {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        setUser(null);
        return null;
      }
    } else {
      const token = localStorage.getItem("stockwise_token") || sessionStorage.getItem("stockwise_token");
      if (!token) {
        setUser(null);
        return null;
      }
    }
    const account = await loadProfile();
    setUser(account);
    return account;
  }

  useEffect(() => {
    refresh()
      .catch(async () => {
        if (supabaseEnabled) await supabase.auth.signOut();
        localStorage.removeItem("stockwise_token");
        sessionStorage.removeItem("stockwise_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      setUser,
      refresh,
      supabaseEnabled,
      async login(email, password, remember) {
        if (!supabaseEnabled) {
          const response = await api.post("/auth/login", { email, password, remember_me: remember });
          storeToken(response.data.access_token, remember);
          setUser(response.data.user);
          return response.data.user;
        }
        setRemember(remember);
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw authError(error);
        try {
          const account = await loadProfile();
          setUser(account);
          return account;
        } catch (err) {
          if (err.response?.data?.details?.code !== "profile_required") throw err;
          const metadata = data.user?.user_metadata || {};
          const response = await api.post("/auth/provision", {
            name: metadata.name,
            role: metadata.role,
            business_name: metadata.business_name,
            join_code: metadata.join_code,
          });
          setUser(response.data.user);
          return response.data.user;
        }
      },
      async register(payload) {
        if (!supabaseEnabled) {
          const response = await api.post("/auth/register", payload);
          storeToken(response.data.access_token, true);
          setUser(response.data.user);
          return response.data.user;
        }
        setRemember(true);
        const { data, error } = await supabase.auth.signUp({
          email: payload.email,
          password: payload.password,
          options: {
            data: {
              name: payload.name,
              role: payload.role,
              business_name: payload.business_name,
              join_code: payload.join_code,
            },
          },
        });
        if (error) throw authError(error);
        if (!data.session) {
          throw authError({
            message: "Confirm the email from Supabase, then log in. For this demo, turn off Confirm email under Authentication in the Supabase dashboard.",
          });
        }
        const response = await api.post("/auth/provision", {
          name: payload.name,
          role: payload.role,
          business_name: payload.business_name,
          join_code: payload.join_code,
        });
        setUser(response.data.user);
        return response.data.user;
      },
      async logout() {
        if (supabaseEnabled) {
          await supabase.auth.signOut();
        } else {
          try {
            await api.post("/auth/logout");
          } catch {
            /* The local session is cleared either way. */
          }
        }
        localStorage.removeItem("stockwise_token");
        sessionStorage.removeItem("stockwise_token");
        setUser(null);
      },
      async changePassword({ current_password, new_password, confirm_password }) {
        if (new_password !== confirm_password) {
          throw authError({ message: "Password and confirmation do not match." });
        }
        if (!supabaseEnabled) {
          await api.put("/auth/password", { current_password, new_password, confirm_password });
          return;
        }
        const signedIn = await supabase.auth.signInWithPassword({ email: user.email, password: current_password });
        if (signedIn.error) throw authError({ message: "Current password is incorrect." });
        const updated = await supabase.auth.updateUser({ password: new_password });
        if (updated.error) throw authError(updated.error);
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

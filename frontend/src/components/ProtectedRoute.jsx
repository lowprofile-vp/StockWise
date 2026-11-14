import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Spinner from "./Spinner";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Checking your session" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!user.setup_complete) {
    if (user.role !== "admin") {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
          <div className="max-w-md rounded-xl bg-white p-6 shadow-sm">
            <h1 className="text-xl font-semibold text-slate-900">Workspace setup is still open</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {user.business_name} is not ready yet. Ask the owner to finish business setup, then sign in again.
            </p>
          </div>
        </div>
      );
    }
    if (location.pathname !== "/setup") return <Navigate to="/setup" replace />;
  } else if (location.pathname === "/setup") {
    return <Navigate to="/overview" replace />;
  }
  return <Outlet />;
}

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import BusinessSetup from "./pages/BusinessSetup";
import Overview from "./pages/Overview";
import Inventory from "./pages/Inventory";
import ProductDetails from "./pages/ProductDetails";
import SalesUsage from "./pages/SalesUsage";
import RestockCenter from "./pages/RestockCenter";
import Suppliers from "./pages/Suppliers";
import Analytics from "./pages/Analytics";
import Simulations from "./pages/Simulations";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/setup" element={<BusinessSetup />} />
              <Route element={<AppLayout />}>
                <Route path="/overview" element={<Overview />} />
                <Route path="/inventory" element={<Inventory />} />
                <Route path="/inventory/:productId" element={<ProductDetails />} />
                <Route path="/sales" element={<SalesUsage />} />
                <Route path="/restock" element={<RestockCenter />} />
                <Route path="/suppliers" element={<Suppliers />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/simulations" element={<Simulations />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}

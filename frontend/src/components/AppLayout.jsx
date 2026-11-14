import { useState } from "react";
import { Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

export default function AppLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar open={open} onClose={() => setOpen(false)} businessName={user?.business_name} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar onMenu={() => setOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

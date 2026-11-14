import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  ClipboardList,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  ShoppingCart,
  Truck,
  X,
} from "lucide-react";

const ITEMS = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/sales", label: "Sales & Usage", icon: ShoppingCart },
  { to: "/restock", label: "Restock Center", icon: ClipboardList },
  { to: "/suppliers", label: "Suppliers", icon: Truck },
  { to: "/analytics", label: "Analytics & Forecasts", icon: LineChart },
  { to: "/simulations", label: "Simulations", icon: FlaskConical },
  { to: "/reports", label: "Reports", icon: BarChart3 },
];

export default function Sidebar({ open, onClose, businessName }) {
  return (
    <>
      <div className={`fixed inset-0 z-30 bg-slate-900/40 lg:hidden ${open ? "block" : "hidden"}`} onClick={onClose} />
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-900 text-slate-300 transition lg:static lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between px-5 py-5">
          <div>
            <p className="text-lg font-semibold tracking-tight text-white">StockWise</p>
            <p className="mt-1 truncate text-xs text-slate-400">{businessName}</p>
          </div>
          <button type="button" className="rounded-md p-1 text-slate-300 lg:hidden" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    isActive ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <p className="px-5 py-4 text-xs leading-5 text-slate-500">Estimates use recent demand. They are not a guarantee of future sales.</p>
      </aside>
    </>
  );
}

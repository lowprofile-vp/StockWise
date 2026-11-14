import { useEffect, useState } from "react";
import { Bell, LogOut, Menu, Search, Settings, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Navbar({ onMenu }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [notes, setNotes] = useState([]);
  const [openNotes, setOpenNotes] = useState(false);
  const [openProfile, setOpenProfile] = useState(false);

  useEffect(() => {
    const handle = setTimeout(async () => {
      if (query.trim().length < 2) {
        setResults(null);
        return;
      }
      try {
        const response = await api.get("/search", { params: { q: query.trim() } });
        setResults(response.data.data);
      } catch {
        setResults(null);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    api.get("/notifications").then((response) => setNotes(response.data.data || [])).catch(() => setNotes([]));
  }, []);

  async function signOut() {
    await logout();
    navigate("/login");
  }

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
      <button type="button" className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={onMenu} aria-label="Open menu">
        <Menu size={18} />
      </button>
      <div className="relative min-w-0 flex-1 max-w-xl">
        <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          aria-label="Search products, suppliers, and orders"
          className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
          placeholder="Search products, suppliers, or PO-0001"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {results ? (
          <div className="absolute z-30 mt-2 w-full rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <ResultGroup title="Products" rows={results.products} onPick={(row) => navigate(`/inventory/${row.product_id}`)} label={(row) => `${row.code} · ${row.name}`} />
            <ResultGroup title="Suppliers" rows={results.suppliers} onPick={() => navigate("/suppliers")} label={(row) => row.name} />
            <ResultGroup title="Orders" rows={results.purchase_orders} onPick={() => navigate("/restock")} label={(row) => `${row.code} · ${row.status}`} />
            {!results.products.length && !results.suppliers.length && !results.purchase_orders.length ? (
              <p className="px-2 py-3 text-sm text-slate-500">No matches.</p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="relative">
        <button type="button" className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" aria-label="Notifications" onClick={() => { setOpenNotes((value) => !value); setOpenProfile(false); }}>
          <Bell size={18} />
          {notes.length ? <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-600" /> : null}
        </button>
        {openNotes ? (
          <div className="absolute right-0 z-30 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <p className="px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">Notifications</p>
            <div className="max-h-80 overflow-auto">
              {notes.length ? notes.map((note) => (
                <button key={note.id} type="button" className="block w-full rounded-lg px-2 py-2 text-left hover:bg-slate-50" onClick={() => { setOpenNotes(false); navigate(note.href); }}>
                  <p className="text-sm font-medium text-slate-800">{note.title}</p>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-500">{note.body}</p>
                </button>
              )) : <p className="px-2 py-3 text-sm text-slate-500">No open alerts.</p>}
            </div>
          </div>
        ) : null}
      </div>
      <div className="relative">
        <button type="button" className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100" onClick={() => { setOpenProfile((value) => !value); setOpenNotes(false); }}>
          <UserRound size={18} className="text-slate-600" />
          <span className="hidden max-w-32 truncate font-medium text-slate-800 sm:inline">{user?.name}</span>
        </button>
        {openProfile ? (
          <div className="absolute right-0 z-30 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <p className="px-2 py-1 text-xs text-slate-500">{user?.role_label}</p>
            <Link to="/settings" className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-slate-50" onClick={() => setOpenProfile(false)}>
              <Settings size={16} /> Business settings
            </Link>
            <button type="button" className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-red-700 hover:bg-red-50" onClick={signOut}>
              <LogOut size={16} /> Log out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

function ResultGroup({ title, rows, onPick, label }) {
  if (!rows?.length) return null;
  return (
    <div className="mb-1">
      <p className="px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-400">{title}</p>
      {rows.map((row) => (
        <button key={row.product_id || row.supplier_id || row.order_id} type="button" className="block w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-50" onClick={() => onPick(row)}>
          {label(row)}
        </button>
      ))}
    </div>
  );
}

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const links = [
  { to: "/", label: "Overview" },
  { to: "/products", label: "Products" },
  { to: "/forecasting", label: "Forecasting" },
  { to: "/analytics", label: "Analytics" },
  { to: "/sales", label: "Sales" },
  { to: "/model", label: "Model" },
  { to: "/reports", label: "Reports" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-stone-200 bg-white lg:border-b-0 lg:border-r">
        <div className="px-6 py-6">
          <p className="font-display text-3xl">Atelier</p>
          <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Demand forecast</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-6 py-6 text-sm text-stone-500 lg:block">
          <p className="font-medium text-stone-800">{user?.name}</p>
          <p>{user?.role}</p>
          <button className="mt-3 text-rose-800" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="p-4 sm:p-8">
        <Outlet />
      </main>
    </div>
  );
}

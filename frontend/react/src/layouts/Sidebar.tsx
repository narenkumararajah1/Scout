import { NavLink } from "react-router-dom";

const NAV_ITEMS: Array<{ to: string; label: string; end: boolean }> = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/companies", label: "Companies", end: false },
  { to: "/analytics", label: "Analytics", end: false },
  { to: "/notifications", label: "Notifications", end: false },
  { to: "/settings", label: "Settings", end: false },
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">Scout</div>
      <ul className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink to={item.to} end={item.end} className={({ isActive }) => (isActive ? "active" : undefined)}>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

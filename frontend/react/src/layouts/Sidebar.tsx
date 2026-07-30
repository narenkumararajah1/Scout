import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { RecentCompanies } from "../components/ui/RecentCompanies";

const NAV_ITEMS: Array<{ to: string; label: string; end: boolean }> = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/companies", label: "Companies", end: false },
  { to: "/analytics", label: "Analytics", end: false },
  { to: "/sales-enablement", label: "Sales Enablement", end: false },
  { to: "/ask-scout", label: "Ask Scout", end: false },
  // First-class rather than buried under Administration
  // (10_NAVIGATION_IMPROVEMENTS.md: "The library should feel like an
  // integral part of Scout rather than an administrative tool"), and
  // placed next to Ask Scout because it is what grounds those answers.
  { to: "/knowledge", label: "Knowledge Library", end: false },
  { to: "/notifications", label: "Notifications", end: false },
  { to: "/administration", label: "Administration", end: false },
  { to: "/settings", label: "Settings", end: false },
];

export function Sidebar() {
  // Below 768px the nav collapses into this button-triggered drawer
  // (desktop keeps the always-visible column - see .sidebar-toggle's
  // display:none default in index.css, only flipped on in that
  // breakpoint). isOpen only ever matters on mobile/tablet: on desktop
  // the toggle button and backdrop are CSS-hidden regardless of state.
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  return (
    <>
      <nav className="sidebar">
        <div className="sidebar-brand">Scout</div>
        <button
          type="button"
          className={`sidebar-toggle${isOpen ? " open" : ""}`}
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
          aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
        >
          <span className="sidebar-toggle-bar" />
          <span className="sidebar-toggle-bar" />
          <span className="sidebar-toggle-bar" />
        </button>
        <ul className={`sidebar-nav${isOpen ? " open" : ""}`}>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end} className={({ isActive }) => (isActive ? "active" : undefined)}>
                {item.label}
              </NavLink>
            </li>
          ))}
          {/* Inside the same <ul>, which below 768px is the slide-out
              drawer itself - so the switcher travels with it rather than
              being stranded in the collapsed top bar (V3 Enhancements
              Phase 6). */}
          <RecentCompanies />
        </ul>
      </nav>
      {isOpen && <div className="sidebar-backdrop" onClick={() => setIsOpen(false)} />}
    </>
  );
}

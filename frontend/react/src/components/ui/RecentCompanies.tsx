// The quick company switcher (V3 Enhancements Phase 6 -
// docs/v3-enhancements/10_NAVIGATION_IMPROVEMENTS.md's Company
// Navigation: "Users should not repeatedly navigate through long company
// lists").
//
// Lives in the sidebar, under the primary nav, because that is the one
// element visible from every page - the doc's complaint is about the
// round trip through Companies, and a switcher that itself needs
// navigating to would not remove it.
//
// **Reads visit data that already existed.** The company page has
// recorded `last_viewed_at` on every open since the earlier roadmap's
// "What Changed Since Last Visit"; this is the first thing to read it
// for navigation. Nothing new is recorded to make this work.
//
// Renders nothing at all until a company has been opened. An empty
// "Recent" heading on a first run is clutter that teaches the user
// nothing, and the list appears on its own the moment it has content.
import { NavLink } from "react-router-dom";
import { useRecentCompanies } from "../../hooks/useRecentCompanies";

export function RecentCompanies() {
  const { data } = useRecentCompanies();

  // No loading or error state on purpose: this is a convenience beside
  // navigation that always works, so a spinner or an error where a
  // shortcut list would be is more disruptive than showing nothing.
  const companies = data ?? [];
  if (companies.length === 0) {
    return null;
  }

  // Rendered as an <li> inside the primary nav's <ul>, not as a sibling
  // of it. Below 768px that <ul> *is* the slide-out drawer, so anything
  // outside it would be stranded in the collapsed top bar - nesting keeps
  // the switcher available on mobile with no drawer CSS of its own.
  return (
    <li className="sidebar-recent">
      <h2 className="sidebar-section-heading">Recent</h2>
      <ul>
        {companies.map((company) => (
          <li key={company.company_id}>
            <NavLink
              to={`/companies/${company.company_id}`}
              className={({ isActive }) => (isActive ? "active" : undefined)}
              title={company.industry ? `${company.company_name} - ${company.industry}` : company.company_name}
            >
              {company.company_name}
            </NavLink>
          </li>
        ))}
      </ul>
    </li>
  );
}

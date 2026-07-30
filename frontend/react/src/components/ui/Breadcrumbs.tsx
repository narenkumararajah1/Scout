// Breadcrumb trail (V3 Enhancements Phase 6 -
// docs/v3-enhancements/10_NAVIGATION_IMPROVEMENTS.md's Breadcrumbs
// section, which asks for a trail like "Companies > Microsoft > Meeting
// Brief" rather than a single step back).
//
// **This replaces the `breadcrumb-back` links, it does not join them.**
// Every artifact page previously rendered "← Back to company" - one
// level, and without naming the company, so a user arriving from a
// search result could not tell whose brief they were reading. Leaving
// both would give two ways back to the same place, which is exactly what
// that document lists as a problem ("Why are there multiple ways to do
// the same thing?").
//
// The company name is resolved here rather than passed in, so adopting
// this on a page is a one-line change and no page has to add a query it
// did not already need. While that resolves, the crumb reads "Company" -
// a stable placeholder of roughly the right width, rather than a blank
// that shifts the row when it fills in.
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { useCompany } from "../../hooks/useCompany";

interface Crumb {
  label: string;
  to: string;
}

interface BreadcrumbsProps {
  /** Inserts Companies > <name> ahead of `current`. */
  companyId?: string;
  /** Explicit trail for pages that are not company-scoped. */
  trail?: Crumb[];
  /** The current page. Rendered as text, never a link to itself. */
  current: string;
}

export function Breadcrumbs({ companyId, trail, current }: BreadcrumbsProps) {
  const companyQuery = useCompany(companyId);

  const crumbs: Crumb[] = [...(trail ?? [])];
  if (companyId) {
    crumbs.push({ label: "Companies", to: "/companies" });
    crumbs.push({ label: companyQuery.data?.name ?? "Company", to: `/companies/${companyId}` });
  }

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {crumbs.map((crumb) => (
        <Fragment key={crumb.to}>
          <Link to={crumb.to}>{crumb.label}</Link>
          <span className="breadcrumb-separator" aria-hidden="true">
            /
          </span>
        </Fragment>
      ))}
      {/* aria-current marks the end of the trail for a screen reader,
          which cannot infer it from the missing link the way sighted
          readers do from position. */}
      <span className="breadcrumb-current" aria-current="page">
        {current}
      </span>
    </nav>
  );
}

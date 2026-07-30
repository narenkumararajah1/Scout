// Jump between a company's artifacts without going back through its page
// (V3 Enhancements Phase 6 - 10_NAVIGATION_IMPROVEMENTS.md's Report
// Navigation: move between Company > Opportunity > Meeting Brief > Sales
// Playbook > Outreach > Report "without unnecessary navigation steps").
//
// **The gap this closes is lateral, not forward.** The Meeting Brief page
// already offers forward actions - buttons that *generate* an outreach
// draft or a report. What no page offered was reaching a sibling that
// already exists: from a Sales Playbook, the company's Meeting Brief was
// two navigations away (back to the company, then scroll to the right
// card). Duplicating the generation buttons here instead would have put
// two different "Generate Report" controls on one page.
//
// Shows the most recent of each other artifact type. Most recent rather
// than all of them, because this is a jump control beside the content,
// not a second index of the company - the full lists stay on the company
// page, which the breadcrumb above already links to.
import { Link } from "react-router-dom";
import { useIntelligenceReports } from "../../hooks/useIntelligenceReports";
import { useMeetingBriefs } from "../../hooks/useMeetingBriefs";
import { useOutreachDrafts } from "../../hooks/useOutreachDrafts";
import { useSalesPlaybooks } from "../../hooks/useSalesPlaybooks";

export type ArtifactKind = "playbook" | "brief" | "outreach" | "report";

interface RelatedArtifactsProps {
  companyId: string;
  /** The page this is rendered on, so it never links to itself. */
  current: ArtifactKind;
}

export function RelatedArtifacts({ companyId, current }: RelatedArtifactsProps) {
  const playbooks = useSalesPlaybooks(companyId);
  const briefs = useMeetingBriefs(companyId);
  const drafts = useOutreachDrafts(companyId);
  const reports = useIntelligenceReports(companyId);

  const links: Array<{ kind: ArtifactKind; label: string; to: string }> = [];

  const playbook = playbooks.data?.[0];
  if (playbook && current !== "playbook") {
    links.push({ kind: "playbook", label: "Sales Playbook", to: `/sales-playbooks/${playbook.id}` });
  }
  const brief = briefs.data?.[0];
  if (brief && current !== "brief") {
    links.push({ kind: "brief", label: "Meeting Brief", to: `/meeting-briefs/${brief.id}` });
  }
  const draft = drafts.data?.[0];
  if (draft && current !== "outreach") {
    links.push({ kind: "outreach", label: "Outreach Draft", to: `/outreach-drafts/${draft.id}` });
  }
  const report = reports.data?.[0];
  if (report && current !== "report") {
    links.push({ kind: "report", label: "Report", to: report.to });
  }

  // Nothing to jump to is the normal state for a company with one
  // artifact, and an empty "Related" strip would be noise on exactly the
  // pages that have least to show.
  if (links.length === 0) {
    return null;
  }

  return (
    <nav className="related-artifacts" aria-label="Related intelligence for this company">
      <span className="related-artifacts-label">Also for this company</span>
      {links.map((link) => (
        <Link key={link.kind} to={link.to}>
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

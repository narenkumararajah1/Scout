import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompany } from "../hooks/useCompany";
import { useCompanyIntelligence } from "../hooks/useCompanyIntelligence";
import { companyService } from "../services/companyService";
import { getErrorMessage } from "../utils/errors";

export function CompanyDetailsPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const companyQuery = useCompany(companyId);
  const intelligenceQuery = useCompanyIntelligence(companyId);
  const queryClient = useQueryClient();

  const toggleMonitoring = useMutation({
    mutationFn: () => {
      const company = companyQuery.data;
      if (!company) {
        throw new Error("Company not loaded yet.");
      }
      return company.monitoring_status === "enabled"
        ? companyService.disableMonitoring(company.id)
        : companyService.enableMonitoring(company.id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["company", companyId] });
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  if (!companyId) {
    return <ErrorState message="No company selected." />;
  }

  if (companyQuery.isLoading) {
    return <LoadingState message="Loading company..." />;
  }

  if (companyQuery.isError || !companyQuery.data) {
    return <ErrorState message={companyQuery.error ? getErrorMessage(companyQuery.error) : "Company not found."} />;
  }

  const company = companyQuery.data;
  const intelligence = intelligenceQuery.data;

  return (
    <div className="company-details-page">
      <div className="page-header">
        <h1>{company.name}</h1>
        <Badge
          label={company.monitoring_status}
          variant={company.monitoring_status === "enabled" ? "success" : "neutral"}
        />
        <button type="button" onClick={() => toggleMonitoring.mutate()} disabled={toggleMonitoring.isPending}>
          {company.monitoring_status === "enabled" ? "Disable monitoring" : "Enable monitoring"}
        </button>
      </div>

      {toggleMonitoring.isError && <p className="form-error">{getErrorMessage(toggleMonitoring.error)}</p>}

      <Card title="Overview">
        <dl className="company-overview">
          <dt>Industry</dt>
          <dd>{company.industry ?? "Unknown"}</dd>
          <dt>Headquarters</dt>
          <dd>{company.headquarters ?? "Unknown"}</dd>
          <dt>Website</dt>
          <dd>{company.website ?? "Unknown"}</dd>
        </dl>
      </Card>

      <Card title="Company Intelligence">
        {intelligenceQuery.isLoading ? (
          <LoadingState message="Loading intelligence..." />
        ) : intelligenceQuery.isError ? (
          <ErrorState message={getErrorMessage(intelligenceQuery.error)} />
        ) : !intelligence ? (
          <EmptyState message="No intelligence available yet." />
        ) : (
          <div className="intelligence-sections">
            <section>
              <h3>Technologies</h3>
              {intelligence.technologies.length === 0 ? (
                <EmptyState message="No technologies detected yet." />
              ) : (
                <ul>
                  {intelligence.technologies.map((tech) => (
                    <li key={tech.id}>
                      {tech.name}
                      {tech.category ? ` - ${tech.category}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Business Initiatives</h3>
              {intelligence.business_initiatives.length === 0 ? (
                <EmptyState message="No business initiatives detected yet." />
              ) : (
                <ul>
                  {intelligence.business_initiatives.map((initiative) => (
                    <li key={initiative.id}>{initiative.name}</li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Executives</h3>
              {intelligence.executives.length === 0 ? (
                <EmptyState message="No executives identified yet." />
              ) : (
                <ul>
                  {intelligence.executives.map((executive) => (
                    <li key={executive.id}>
                      {executive.name}
                      {executive.title ? ` - ${executive.title}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Recent Signals</h3>
              {intelligence.recent_signals.length === 0 ? (
                <EmptyState message="No recent signals." />
              ) : (
                <ul>
                  {intelligence.recent_signals.map((signal) => (
                    <li key={signal.id}>{signal.title}</li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Glean Knowledge</h3>
              {intelligence.glean_knowledge.length === 0 ? (
                <EmptyState message="No Glean results (Glean may not be configured)." />
              ) : (
                <ul>
                  {intelligence.glean_knowledge.map((item) => (
                    <li key={`${item.source}-${item.content}`}>{item.content}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </Card>
    </div>
  );
}

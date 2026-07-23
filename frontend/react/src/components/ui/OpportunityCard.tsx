import { Badge } from "./Badge";
import { formatConfidence } from "../../utils/reportFormatting";

interface OpportunityCardProps {
  title: string | null;
  priority?: number | null;
  confidence?: number | null;
  focus?: string | null;
  description: string;
  recommendedServices?: string[];
}

// One opportunity, fully self-contained: title as a heading, Priority
// and Confidence pulled out as badges instead of sitting inside the
// sentence, then the description as normal prose underneath.
export function OpportunityCard({
  title,
  priority,
  confidence,
  focus,
  description,
  recommendedServices,
}: OpportunityCardProps) {
  const confidenceLabel = formatConfidence(confidence ?? null);

  return (
    <div className="opportunity-card">
      <div className="opportunity-card-header">
        <h4 className="opportunity-card-title">{title ?? "Opportunity"}</h4>
        <div className="opportunity-card-badges">
          {priority !== null && priority !== undefined && (
            <Badge label={`Priority ${priority}`} variant="warning" />
          )}
          {confidenceLabel && <Badge label={`Confidence ${confidenceLabel}`} variant="success" />}
        </div>
      </div>
      {focus && <p className="opportunity-card-focus">{focus}</p>}
      <p className="opportunity-card-description">{description}</p>
      {recommendedServices && recommendedServices.length > 0 && (
        <ul className="bullet-list bullet-list-compact">
          {recommendedServices.map((service, index) => (
            <li key={index} className="bullet-list-item">
              {service}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

import { Badge } from "./Badge";
import { formatConfidence } from "../../utils/reportFormatting";

interface CapabilityCardProps {
  name: string;
  confidence: number | null;
  description: string;
}

// One capability match: the capability name as a heading (highlighted,
// per "important information should stand out"), confidence pulled out
// as a badge, reasoning as prose underneath.
export function CapabilityCard({ name, confidence, description }: CapabilityCardProps) {
  const confidenceLabel = formatConfidence(confidence);

  return (
    <div className="capability-card">
      <div className="capability-card-header">
        <h4 className="capability-card-name">{name}</h4>
        {confidenceLabel && <Badge label={`Confidence ${confidenceLabel}`} variant="success" />}
      </div>
      <p className="capability-card-description">{description}</p>
    </div>
  );
}

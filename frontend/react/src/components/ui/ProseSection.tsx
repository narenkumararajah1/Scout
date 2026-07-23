import { splitIntoReadableParagraphs } from "../../utils/reportFormatting";

interface ProseSectionProps {
  text: string;
  lead?: boolean;
}

// Breaks a long generated paragraph into short, scannable paragraphs -
// same words, more whitespace. `lead` gives the first paragraph a
// slightly larger, callout treatment for sections meant to be read
// first (e.g. an Executive Summary).
export function ProseSection({ text, lead = false }: ProseSectionProps) {
  const paragraphs = splitIntoReadableParagraphs(text);
  return (
    <div className={lead ? "prose-section prose-section-lead" : "prose-section"}>
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
  );
}

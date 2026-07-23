// Presentation-only text parsing for report readability. None of this
// touches report content or generation - it only recognizes structure
// the LLM already writes into these fields (numbered lists, "Opportunity
// N: '...' carries a Priority of X and a Confidence Score of Y", "First,
// 'Capability' aligns with a Z confidence score") so it can be rendered
// as lists/cards instead of one dense paragraph. Every parser falls back
// to returning the original text untouched when the expected pattern
// isn't found, so no content is ever dropped or misrepresented.

export function splitIntoSentences(text: string): string[] {
  // Splits at a sentence-ending punctuation mark followed by whitespace
  // and a capital letter - deliberately does NOT split on a bare
  // "digit.digit" (e.g. a "0.95 confidence score"), since there's no
  // capital letter immediately after that period.
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z])/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

// Groups sentences into short paragraphs instead of one long block -
// "avoid large paragraphs" without cutting any content.
export function splitIntoReadableParagraphs(text: string, sentencesPerParagraph = 2): string[] {
  const sentences = splitIntoSentences(text);
  if (sentences.length <= sentencesPerParagraph) {
    return [text.trim()];
  }
  const paragraphs: string[] = [];
  for (let i = 0; i < sentences.length; i += sentencesPerParagraph) {
    paragraphs.push(sentences.slice(i, i + sentencesPerParagraph).join(" "));
  }
  return paragraphs;
}

// Recognizes "1. First item. 2. Second item. 3. Third item." (no
// newlines between items, as the LLM writes it) and splits it into one
// string per item. Only returns a result when the markers form a clean
// 1, 2, 3, ... sequence - anything else (prose that happens to contain
// a number, out-of-order markers, a single item) returns null so the
// caller can fall back to rendering the original text untouched.
export function splitNumberedList(text: string): string[] | null {
  const markerPattern = /(?:^|\s)(\d{1,2})\.\s+/g;
  const markers: Array<{ start: number; matchLength: number; num: number }> = [];
  let match: RegExpExecArray | null;
  while ((match = markerPattern.exec(text)) !== null) {
    markers.push({ start: match.index, matchLength: match[0].length, num: Number(match[1]) });
  }

  if (markers.length < 2 || !markers.every((marker, index) => marker.num === index + 1)) {
    return null;
  }

  const items = markers.map((marker, index) => {
    const contentStart = marker.start + marker.matchLength;
    const contentEnd = index + 1 < markers.length ? markers[index + 1].start : text.length;
    return text.slice(contentStart, contentEnd).trim();
  });

  return items.every(Boolean) ? items : null;
}

export interface ParsedOpportunity {
  number: number;
  title: string | null;
  priority: number | null;
  confidence: number | null;
  description: string;
}

export interface ParsedOpportunities {
  intro: string | null;
  items: ParsedOpportunity[];
}

// Recognizes the "Opportunity N: '<title>' carries a Priority of P and
// a Confidence Score of C, <description>." shape.
export function parseOpportunitiesText(text: string): ParsedOpportunities | null {
  const pattern =
    /Opportunity\s+(\d+):\s*['"]([^'"]+)['"]\s*carries a Priority of\s*(\d+)\s*and a Confidence Score of\s*([\d.]+),?\s*/gi;
  const matches = [...text.matchAll(pattern)];
  if (matches.length === 0) {
    return null;
  }

  const firstIndex = matches[0].index ?? 0;
  const intro = text.slice(0, firstIndex).trim() || null;

  const items: ParsedOpportunity[] = matches.map((match, index) => {
    const descriptionStart = (match.index ?? 0) + match[0].length;
    const descriptionEnd = index + 1 < matches.length ? (matches[index + 1].index ?? text.length) : text.length;
    return {
      number: Number(match[1]),
      title: match[2],
      priority: Number(match[3]),
      confidence: Number(match[4]),
      description: text.slice(descriptionStart, descriptionEnd).trim(),
    };
  });

  return { intro, items };
}

export interface ParsedCapability {
  name: string;
  confidence: number | null;
  description: string;
}

export interface ParsedCapabilities {
  intro: string | null;
  items: ParsedCapability[];
}

const ORDINAL_WORDS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"];

// Recognizes the "First, 'Capability Name' aligns with a C confidence
// score, <description>." shape (repeated with Second, Third, ...).
export function parseCapabilityAlignmentText(text: string): ParsedCapabilities | null {
  const ordinalGroup = ORDINAL_WORDS.join("|");
  const pattern = new RegExp(
    `(?:${ordinalGroup}),?\\s*['"]([^'"]+)['"]\\s*aligns with an?\\s*([\\d.]+)\\s*confidence score,?\\s*`,
    "gi",
  );
  const matches = [...text.matchAll(pattern)];
  if (matches.length === 0) {
    return null;
  }

  const firstIndex = matches[0].index ?? 0;
  const intro = text.slice(0, firstIndex).trim() || null;

  const items: ParsedCapability[] = matches.map((match, index) => {
    const descriptionStart = (match.index ?? 0) + match[0].length;
    const descriptionEnd = index + 1 < matches.length ? (matches[index + 1].index ?? text.length) : text.length;
    return {
      name: match[1],
      confidence: Number(match[2]),
      description: text.slice(descriptionStart, descriptionEnd).trim(),
    };
  });

  return { intro, items };
}

export function formatConfidence(confidence: number | null): string | null {
  if (confidence === null || Number.isNaN(confidence)) {
    return null;
  }
  return `${Math.round(confidence * 100)}%`;
}

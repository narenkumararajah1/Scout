// Asks Scout's memory, once per service it actually recommends, whether
// there is real project experience behind that recommendation.
//
// There is no persisted link from a KnowledgeDocument to the
// opportunities that used it - the opportunity carries
// recommended_services (a name) and reasoning (prose), never a document
// id. So the join has to be made at read time, and semantic search is
// the only honest way to make it: the same retrieval path that grounds
// Scout's own answers is asked the same question the recommendation
// implies.
//
// One request per service, in parallel, each cached under the same key
// shape as useKnowledgeSearch so a probe and a manual search for the
// same text share one cache entry.
import { useQueries } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";
import type { KnowledgeReference, KnowledgeSearchResult } from "../types/knowledgeDocument";

const PROBE_LIMIT = 10;
// Evidence changes only when the corpus is re-ingested, which is a rare,
// manual act - re-probing on every mount would cost nine embeddings for
// an answer that cannot have moved.
const PROBE_STALE_MS = 5 * 60 * 1000;

export interface EvidenceItem {
  documentId: string;
  title: string;
  relevance: number;
  excerpt: string;
}

export interface ServiceEvidence {
  service: string;
  isLoading: boolean;
  isError: boolean;
  // The curated capability entity: what Scout defines itself as able to
  // do. Present for every service in production, which is the point -
  // the claim is never the weak link, the proof is.
  claim: KnowledgeReference | null;
  claimRelevance: number | null;
  // Distinct documents, best passage per document, strongest first.
  proof: EvidenceItem[];
  strongestProof: number | null;
  // How far the closest real project falls short of the capability
  // statement. Null until both halves have arrived.
  gap: number | null;
}

function readEvidence(service: string, data: KnowledgeSearchResult | undefined): {
  claim: KnowledgeReference | null;
  proof: EvidenceItem[];
} {
  const refs = data?.results ?? [];

  // Prefer the capability that is literally this service; fall back to
  // whatever capability the retrieval surfaced, so a renamed service
  // still shows its nearest definition rather than nothing.
  const claim =
    refs.find((ref) => ref.entity_type === "capability" && ref.name === service) ??
    refs.find((ref) => ref.entity_type === "capability") ??
    null;

  // A document can match on several passages; only its strongest counts,
  // otherwise one verbose case study would look like broad experience.
  const best = new Map<string, EvidenceItem>();
  for (const ref of refs) {
    if (ref.entity_type !== "document" || !ref.document_id || ref.relevance === null) {
      continue;
    }
    const existing = best.get(ref.document_id);
    if (existing && existing.relevance >= ref.relevance) {
      continue;
    }
    best.set(ref.document_id, {
      documentId: ref.document_id,
      title: ref.name ?? "Untitled document",
      relevance: ref.relevance,
      excerpt: ref.content,
    });
  }

  return {
    claim,
    proof: [...best.values()].sort((a, b) => b.relevance - a.relevance),
  };
}

export function useServiceEvidence(services: string[]): {
  evidence: ServiceEvidence[];
  settledCount: number;
  isSettled: boolean;
} {
  const results = useQueries({
    queries: services.map((service) => ({
      queryKey: ["knowledge-search", service, undefined, PROBE_LIMIT],
      queryFn: () => knowledgeService.search(service, { limit: PROBE_LIMIT }),
      staleTime: PROBE_STALE_MS,
    })),
  });

  const evidence = services.map((service, index) => {
    const result = results[index];
    const { claim, proof } = readEvidence(service, result?.data);
    const claimRelevance = claim?.relevance ?? null;
    const strongestProof = proof[0]?.relevance ?? null;

    return {
      service,
      isLoading: result?.isLoading ?? true,
      isError: result?.isError ?? false,
      claim,
      claimRelevance,
      proof,
      strongestProof,
      gap:
        claimRelevance !== null && strongestProof !== null
          ? claimRelevance - strongestProof
          : null,
    };
  });

  const settledCount = results.filter((result) => !result.isLoading).length;

  return {
    evidence,
    settledCount,
    isSettled: services.length > 0 && settledCount === services.length,
  };
}

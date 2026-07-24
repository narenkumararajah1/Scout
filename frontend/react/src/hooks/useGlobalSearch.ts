import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchService } from "../services/searchService";

const DEBOUNCE_MS = 300;

// Priority 3 (Global Search): debounces the raw keystroke value before
// firing a request, so typing doesn't send one request per character.
export function useGlobalSearch() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedQuery(query.trim()), DEBOUNCE_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  const resultsQuery = useQuery({
    queryKey: ["global-search", debouncedQuery],
    queryFn: () => searchService.search(debouncedQuery),
    enabled: debouncedQuery.length > 0,
  });

  return { query, setQuery, results: resultsQuery.data, isLoading: resultsQuery.isLoading };
}

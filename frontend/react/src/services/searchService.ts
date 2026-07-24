// Global Search domain operations (Priority 3).
import { apiRequestData } from "../api/client";
import type { SearchResults } from "../types/searchResults";

export const searchService = {
  async search(query: string): Promise<SearchResults> {
    return apiRequestData<SearchResults>(`/api/v1/search?q=${encodeURIComponent(query)}`);
  },
};

// Global Search (Priority 3) - available from the persistent header on
// every page. Cmd/Ctrl+K focuses it from anywhere; Escape closes it;
// Up/Down/Enter navigate results without a mouse.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGlobalSearch } from "../../hooks/useGlobalSearch";
import type { SearchCompanyResult, SearchExecutiveResult, SearchOpportunityResult } from "../../types/searchResults";

interface FlatResult {
  key: string;
  label: string;
  sublabel: string;
  to: string;
}

function flattenResults(
  companies: SearchCompanyResult[],
  executives: SearchExecutiveResult[],
  opportunities: SearchOpportunityResult[],
): FlatResult[] {
  return [
    ...companies.map((c) => ({
      key: `company-${c.id}`,
      label: c.name,
      sublabel: c.industry ?? "Company",
      to: `/companies/${c.id}`,
    })),
    ...executives.map((e) => ({
      key: `executive-${e.id}`,
      label: e.name,
      sublabel: [e.title, e.company_name].filter(Boolean).join(" at ") || "Executive",
      to: `/companies/${e.company_id}`,
    })),
    ...opportunities.map((o) => ({
      key: `opportunity-${o.id}`,
      label: o.title,
      sublabel: o.company_name ? `Opportunity at ${o.company_name}` : "Opportunity",
      to: `/companies/${o.company_id}`,
    })),
  ];
}

export function GlobalSearch() {
  const { query, setQuery, results, isLoading } = useGlobalSearch();
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const companies = results?.companies ?? [];
  const executives = results?.executives ?? [];
  const opportunities = results?.opportunities ?? [];
  const flatResults = flattenResults(companies, executives, opportunities);
  const hasQuery = query.trim().length > 0;

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    function handleGlobalKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
    }
    document.addEventListener("keydown", handleGlobalKeyDown);
    return () => document.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  function closeAndClear() {
    setIsOpen(false);
    setQuery("");
    inputRef.current?.blur();
  }

  function goToResult(result: FlatResult) {
    navigate(result.to);
    closeAndClear();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      closeAndClear();
      return;
    }
    if (!isOpen || flatResults.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % flatResults.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + flatResults.length) % flatResults.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      goToResult(flatResults[activeIndex]);
    }
  }

  return (
    <div className="global-search" ref={containerRef}>
      <input
        ref={inputRef}
        type="search"
        className="global-search-input"
        placeholder="Search companies, executives, opportunities... (⌘K)"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        onKeyDown={handleKeyDown}
        aria-label="Global search"
        aria-expanded={isOpen && hasQuery}
        role="combobox"
        aria-haspopup="listbox"
        aria-controls="global-search-results"
      />

      {isOpen && hasQuery && (
        <div className="global-search-results" id="global-search-results" role="listbox">
          {isLoading ? (
            <div className="global-search-status">Searching...</div>
          ) : flatResults.length === 0 ? (
            <div className="global-search-status">No results for "{query}".</div>
          ) : (
            <>
              {companies.length > 0 && (
                <div className="global-search-group">
                  <div className="global-search-group-label">Companies</div>
                  {companies.map((company) => {
                    const flatIndex = flatResults.findIndex((r) => r.key === `company-${company.id}`);
                    return (
                      <button
                        key={company.id}
                        type="button"
                        role="option"
                        aria-selected={flatIndex === activeIndex}
                        className={`global-search-result${flatIndex === activeIndex ? " active" : ""}`}
                        onMouseEnter={() => setActiveIndex(flatIndex)}
                        onClick={() => goToResult(flatResults[flatIndex])}
                      >
                        <span className="global-search-result-label">{company.name}</span>
                        <span className="global-search-result-sublabel">{company.industry ?? "Company"}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              {executives.length > 0 && (
                <div className="global-search-group">
                  <div className="global-search-group-label">Executives</div>
                  {executives.map((executive) => {
                    const flatIndex = flatResults.findIndex((r) => r.key === `executive-${executive.id}`);
                    return (
                      <button
                        key={executive.id}
                        type="button"
                        role="option"
                        aria-selected={flatIndex === activeIndex}
                        className={`global-search-result${flatIndex === activeIndex ? " active" : ""}`}
                        onMouseEnter={() => setActiveIndex(flatIndex)}
                        onClick={() => goToResult(flatResults[flatIndex])}
                      >
                        <span className="global-search-result-label">{executive.name}</span>
                        <span className="global-search-result-sublabel">
                          {[executive.title, executive.company_name].filter(Boolean).join(" at ") || "Executive"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {opportunities.length > 0 && (
                <div className="global-search-group">
                  <div className="global-search-group-label">Opportunities</div>
                  {opportunities.map((opportunity) => {
                    const flatIndex = flatResults.findIndex((r) => r.key === `opportunity-${opportunity.id}`);
                    return (
                      <button
                        key={opportunity.id}
                        type="button"
                        role="option"
                        aria-selected={flatIndex === activeIndex}
                        className={`global-search-result${flatIndex === activeIndex ? " active" : ""}`}
                        onMouseEnter={() => setActiveIndex(flatIndex)}
                        onClick={() => goToResult(flatResults[flatIndex])}
                      >
                        <span className="global-search-result-label">{opportunity.title}</span>
                        <span className="global-search-result-sublabel">
                          {opportunity.company_name ? `Opportunity at ${opportunity.company_name}` : "Opportunity"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

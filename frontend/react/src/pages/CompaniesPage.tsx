import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompanies } from "../hooks/useCompanies";
import { useConfirm } from "../hooks/useConfirm";
import { useRemoveCompany } from "../hooks/useRemoveCompany";
import { companyService } from "../services/companyService";
import { getErrorMessage } from "../utils/errors";

export function CompaniesPage() {
  const companiesQuery = useCompanies();
  const queryClient = useQueryClient();
  const removeCompany = useRemoveCompany();
  const { confirm, confirmDialog } = useConfirm();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [headquarters, setHeadquarters] = useState("");
  const [website, setWebsite] = useState("");
  const [removeError, setRemoveError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  async function handleRemove(companyId: string, companyName: string) {
    if (!(await confirm(`Remove ${companyName}? This can't be undone.`))) {
      return;
    }
    setRemoveError(null);
    removeCompany.mutate(companyId, {
      onError: (error) => setRemoveError(getErrorMessage(error)),
    });
  }

  const createCompany = useMutation({
    mutationFn: () =>
      companyService.createCompany({
        name,
        industry: industry || undefined,
        headquarters: headquarters || undefined,
        website: website || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      setName("");
      setIndustry("");
      setHeadquarters("");
      setWebsite("");
      setIsFormOpen(false);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCompany.mutate();
  }

  const companies = companiesQuery.data ?? [];
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const visibleCompanies = normalizedSearch
    ? companies.filter(
        (company) =>
          company.name.toLowerCase().includes(normalizedSearch) ||
          (company.industry ?? "").toLowerCase().includes(normalizedSearch),
      )
    : companies;

  return (
    <div className="companies-page">
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}
      <div className="page-header">
        <h1>Companies</h1>
        <button type="button" onClick={() => setIsFormOpen((open) => !open)}>
          {isFormOpen ? "Cancel" : "Add Company"}
        </button>
      </div>

      {isFormOpen && (
        <Card title="Add a company">
          <form onSubmit={handleSubmit} className="add-company-form">
            <label htmlFor="company-name">Name</label>
            <input id="company-name" value={name} onChange={(event) => setName(event.target.value)} required />
            <label htmlFor="company-industry">Industry</label>
            <input
              id="company-industry"
              value={industry}
              onChange={(event) => setIndustry(event.target.value)}
            />
            <label htmlFor="company-hq">Headquarters</label>
            <input
              id="company-hq"
              value={headquarters}
              onChange={(event) => setHeadquarters(event.target.value)}
            />
            <label htmlFor="company-website">Website</label>
            <input id="company-website" value={website} onChange={(event) => setWebsite(event.target.value)} />
            {createCompany.isError && <p className="form-error">{getErrorMessage(createCompany.error)}</p>}
            <button type="submit" disabled={createCompany.isPending}>
              {createCompany.isPending ? "Adding..." : "Add company"}
            </button>
          </form>
        </Card>
      )}

      {removeError && <p className="form-error">{removeError}</p>}

      {companies.length > 0 && (
        <input
          type="search"
          className="company-search"
          placeholder="Search companies by name or industry..."
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          aria-label="Search companies"
        />
      )}

      {companiesQuery.isLoading ? (
        <LoadingState />
      ) : companiesQuery.isError ? (
        <ErrorState message={getErrorMessage(companiesQuery.error)} />
      ) : companies.length === 0 ? (
        <EmptyState message="No companies yet. Add one to get started." />
      ) : visibleCompanies.length === 0 ? (
        <EmptyState message={`No companies match "${searchTerm}".`} />
      ) : (
        <ul className="company-list">
          {visibleCompanies.map((company) => (
            <li key={company.id} className="company-list-row">
              <Link to={`/companies/${company.id}`} className="company-list-item">
                <span>{company.name}</span>
                <span>{company.industry ?? "-"}</span>
                <Badge
                  label={company.monitoring_status}
                  variant={company.monitoring_status === "enabled" ? "success" : "neutral"}
                />
              </Link>
              <button
                type="button"
                className="company-remove-button"
                onClick={() => handleRemove(company.id, company.name)}
                disabled={removeCompany.isPending}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

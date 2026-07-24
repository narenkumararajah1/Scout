import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useArchiveCompany } from "../hooks/useArchiveCompany";
import { useCompanies } from "../hooks/useCompanies";
import { useConfirm } from "../hooks/useConfirm";
import { useRemoveCompany } from "../hooks/useRemoveCompany";
import { useRestoreCompany } from "../hooks/useRestoreCompany";
import { companyService } from "../services/companyService";
import { getErrorMessage } from "../utils/errors";

export function CompaniesPage() {
  const [showArchived, setShowArchived] = useState(false);
  const companiesQuery = useCompanies(showArchived);
  const queryClient = useQueryClient();
  const archiveCompany = useArchiveCompany();
  const restoreCompany = useRestoreCompany();
  const removeCompany = useRemoveCompany();
  const { confirm, confirmDialog } = useConfirm();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [headquarters, setHeadquarters] = useState("");
  const [website, setWebsite] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  async function handleArchive(companyId: string, companyName: string) {
    if (!(await confirm(`Archive ${companyName}? You can restore it later from the archived companies view.`))) {
      return;
    }
    setActionError(null);
    archiveCompany.mutate(companyId, {
      onError: (error) => setActionError(getErrorMessage(error)),
    });
  }

  function handleRestore(companyId: string) {
    setActionError(null);
    restoreCompany.mutate(companyId, {
      onError: (error) => setActionError(getErrorMessage(error)),
    });
  }

  async function handlePermanentlyDelete(companyId: string, companyName: string) {
    if (
      !(await confirm(
        `Permanently delete ${companyName}? This cannot be undone and all research history will be lost.`,
      ))
    ) {
      return;
    }
    setActionError(null);
    removeCompany.mutate(companyId, {
      onError: (error) => setActionError(getErrorMessage(error)),
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
        <label className="companies-show-archived">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => setShowArchived(event.target.checked)}
          />
          Show archived
        </label>
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

      {actionError && <p className="form-error">{actionError}</p>}

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
                {company.archived_at ? (
                  <Badge label="Archived" variant="neutral" />
                ) : (
                  <Badge
                    label={company.monitoring_status}
                    variant={company.monitoring_status === "enabled" ? "success" : "neutral"}
                  />
                )}
              </Link>
              {company.archived_at ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleRestore(company.id)}
                    disabled={restoreCompany.isPending}
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    className="company-remove-button"
                    onClick={() => handlePermanentlyDelete(company.id, company.name)}
                    disabled={removeCompany.isPending}
                  >
                    Delete Permanently
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="company-remove-button"
                  onClick={() => handleArchive(company.id, company.name)}
                  disabled={archiveCompany.isPending}
                >
                  Archive
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

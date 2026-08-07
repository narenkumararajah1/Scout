// Administration - the control center for how Scout runs itself.
//
// The things you can actually administer lead the page, in the order you
// reach for them: schedules, recipients, what is in scope, and how the
// automation behaves. Two of those are full CRUD against real endpoints;
// the other two are read-only here because nothing in the API writes them
// (monitoring scope is changed by archiving a company, which the Companies
// page owns, and automation behaviour comes from the environment). Saying
// so is better than a control that silently does nothing.
//
// Above them sit two things, both deliberately small:
//
//   - A summary line stating the net effect of the current configuration,
//     assembled from live config. It survived from an earlier draft where
//     it was the whole page; as one line it still earns its place, because
//     no single panel below can tell you what the arrangement adds up to.
//   - A warning strip, rendered only when something is actually wrong.
//     The steady state is no strip at all.
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompanies } from "../hooks/useCompanies";
import { useConfirm } from "../hooks/useConfirm";
import { useRecipientActions } from "../hooks/useRecipientActions";
import { useRecipients } from "../hooks/useRecipients";
import { useScheduleActions } from "../hooks/useScheduleActions";
import { useSchedules } from "../hooks/useSchedules";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useWorkflowHistory } from "../hooks/useWorkflowHistory";
import type { Recipient } from "../types/recipient";
import type { Schedule } from "../types/schedule";
import { getErrorMessage } from "../utils/errors";

const FREQUENCY_OPTIONS = ["daily", "weekly"];
const CHANNEL_OPTIONS = ["email", "teams"];

function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function RecipientPreferencesForm({
  recipient,
  onSave,
  onCancel,
  isSaving,
}: {
  recipient: Recipient;
  onSave: (input: { preferred_frequency?: string; preferred_company_ids: string[]; preferred_channels: string[] }) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const companiesQuery = useCompanies();
  const [frequency, setFrequency] = useState(recipient.preferred_frequency ?? "");
  const [channels, setChannels] = useState<string[]>(recipient.preferred_channels);
  const [companyIds, setCompanyIds] = useState<string[]>(recipient.preferred_company_ids);
  const companies = companiesQuery.data ?? [];

  return (
    <div className="recipient-preferences-form">
      <label>
        Frequency
        <select value={frequency} onChange={(event) => setFrequency(event.target.value)}>
          <option value="">Not set</option>
          {FREQUENCY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <fieldset>
        <legend>Channels</legend>
        {CHANNEL_OPTIONS.map((channel) => (
          <label key={channel} className="checkbox-label">
            <input
              type="checkbox"
              checked={channels.includes(channel)}
              onChange={() => setChannels((current) => toggleInList(current, channel))}
            />
            {channel}
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>Companies (none selected = all companies)</legend>
        {companies.map((company) => (
          <label key={company.id} className="checkbox-label">
            <input
              type="checkbox"
              checked={companyIds.includes(company.id)}
              onChange={() => setCompanyIds((current) => toggleInList(current, company.id))}
            />
            {company.name}
          </label>
        ))}
      </fieldset>

      <div className="recipient-preferences-actions">
        <button
          type="button"
          onClick={() =>
            onSave({
              preferred_frequency: frequency || undefined,
              preferred_company_ids: companyIds,
              preferred_channels: channels,
            })
          }
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : "Save preferences"}
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ScheduleForm({
  onSubmit,
  isSaving,
  submitLabel,
}: {
  onSubmit: (input: { frequency: string; time: string; target_company_ids: string[] }) => void;
  isSaving: boolean;
  submitLabel: string;
}) {
  const companiesQuery = useCompanies();
  const [frequency, setFrequency] = useState("daily");
  const [time, setTime] = useState("08:00");
  const [companyIds, setCompanyIds] = useState<string[]>([]);
  const companies = companiesQuery.data ?? [];

  return (
    <div className="add-recipient-form">
      <label htmlFor="schedule-frequency">Frequency</label>
      <select id="schedule-frequency" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
        {FREQUENCY_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <label htmlFor="schedule-time">Delivery time</label>
      <input
        id="schedule-time"
        type="time"
        value={time}
        onChange={(event) => setTime(event.target.value)}
        required
      />
      <fieldset>
        <legend>Target companies (none selected = all companies)</legend>
        {companies.map((company) => (
          <label key={company.id} className="checkbox-label">
            <input
              type="checkbox"
              checked={companyIds.includes(company.id)}
              onChange={() => setCompanyIds((current) => toggleInList(current, company.id))}
            />
            {company.name}
          </label>
        ))}
      </fieldset>
      <button
        type="button"
        onClick={() => onSubmit({ frequency, time, target_company_ids: companyIds })}
        disabled={isSaving}
      >
        {isSaving ? "Saving..." : submitLabel}
      </button>
    </div>
  );
}


interface Warning {
  id: string;
  text: string;
  action?: { label: string; target: string };
}

export function AdministrationPage() {
  const { confirm, confirmDialog } = useConfirm();
  const recipientsQuery = useRecipients();
  const { createRecipient, updatePreferences, enableRecipient, disableRecipient, removeRecipient } =
    useRecipientActions();

  const schedulesQuery = useSchedules();
  const { createSchedule, enableSchedule, disableSchedule, deleteSchedule } = useScheduleActions();
  const [isScheduleFormOpen, setIsScheduleFormOpen] = useState(false);
  const [scheduleActionError, setScheduleActionError] = useState<string | null>(null);

  const statusQuery = useSystemStatus();
  const workflowQuery = useWorkflowHistory();
  const companiesQuery = useCompanies();
  const allCompaniesQuery = useCompanies(true);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [channels, setChannels] = useState<string[]>(["email"]);
  const [editingRecipientId, setEditingRecipientId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createRecipient.mutate(
      { name, email, preferred_frequency: frequency, preferred_channels: channels },
      {
        onSuccess: () => {
          setName("");
          setEmail("");
          setFrequency("daily");
          setChannels(["email"]);
          setIsFormOpen(false);
        },
      },
    );
  }

  async function handleRemove(recipient: Recipient) {
    if (!(await confirm(`Remove ${recipient.name}? This can't be undone.`))) {
      return;
    }
    setActionError(null);
    removeRecipient.mutate(recipient.id, { onError: (error) => setActionError(getErrorMessage(error)) });
  }

  async function handleDeleteSchedule(schedule: Schedule) {
    if (!(await confirm(`Delete this ${schedule.frequency} schedule? This can't be undone.`))) {
      return;
    }
    setScheduleActionError(null);
    deleteSchedule.mutate(schedule.id, { onError: (error) => setScheduleActionError(getErrorMessage(error)) });
  }

  const recipients = recipientsQuery.data ?? [];
  const schedules = schedulesQuery.data ?? [];
  const monitored = companiesQuery.data ?? [];
  const archived = (allCompaniesQuery.data ?? []).filter((company) => company.archived_at);
  const status = statusQuery.data;
  const enabledRecipients = recipients.filter((recipient) => recipient.delivery_status !== "disabled");
  const lastRun = (workflowQuery.data ?? [])[0];
  const lastTarget = lastRun?.target_company ?? null;
  const targetIsMonitored = lastTarget !== null && monitored.some((company) => company.name === lastTarget);

  const configReady = statusQuery.isSuccess && recipientsQuery.isSuccess && schedulesQuery.isSuccess;

  // Only what is genuinely wrong, stated in one line. An action is attached
  // only where this page can actually resolve it - offering one that leads
  // nowhere is worse than offering none. In the steady state this list is
  // empty and nothing renders.
  const warnings: Warning[] = [];
  if (configReady && lastTarget !== null && !targetIsMonitored) {
    warnings.push({
      id: "off-portfolio",
      text: `Scheduled runs analysed "${lastTarget}" instead of your monitored companies.`,
    });
  }
  if (configReady && status && !status.scheduler.running) {
    warnings.push({
      id: "scheduler-down",
      text: "The scheduler is stopped. Nothing will run automatically.",
    });
  }
  if (configReady && recipients.length > 0 && enabledRecipients.length === 0) {
    warnings.push({
      id: "no-recipients",
      text: "No recipient is enabled, so reports have nowhere to go.",
      action: { label: "Enable a recipient", target: "#recipients" },
    });
  }

  // Deferred a frame so the scroll runs against the committed layout.
  function scrollTo(selector: string) {
    requestAnimationFrame(() => {
      document.querySelector(selector)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <div className="admin">
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <header className="admin-head">
        <h1>Administration</h1>
        <p className="admin-lede">Schedules, recipients, scope, and how Scout is allowed to act.</p>
      </header>

      {warnings.length > 0 && (
        <div className="admin-warnings" role="status">
          {warnings.map((warning) => (
            <div key={warning.id} className="admin-warning">
              <span className="admin-warning-mark" aria-hidden="true" />
              <p className="admin-warning-text">{warning.text}</p>
              {warning.action && (
                <button
                  type="button"
                  className="admin-warning-action"
                  onClick={() => scrollTo(warning.action!.target)}
                >
                  {warning.action.label}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* --- schedules ---------------------------------------------------- */}
      <section className="admin-panel" id="scheduling" aria-label="Schedules">
        <div className="admin-panel-head">
          <div>
            <h2>Schedules</h2>
            <p className="admin-hint">
              When Scout runs by itself. With nothing set here it falls back to the interval configured in the
              environment.
            </p>
          </div>
          <button type="button" onClick={() => setIsScheduleFormOpen((open) => !open)}>
            {isScheduleFormOpen ? "Cancel" : "Add schedule"}
          </button>
        </div>

        {isScheduleFormOpen && (
          <ScheduleForm
            submitLabel="Add schedule"
            isSaving={createSchedule.isPending}
            onSubmit={(input) => createSchedule.mutate(input, { onSuccess: () => setIsScheduleFormOpen(false) })}
          />
        )}
        {createSchedule.isError && <p className="form-error">{getErrorMessage(createSchedule.error)}</p>}
        {scheduleActionError && <p className="form-error">{scheduleActionError}</p>}

        {schedulesQuery.isLoading ? (
          <LoadingState />
        ) : schedulesQuery.isError ? (
          <ErrorState message={getErrorMessage(schedulesQuery.error)} />
        ) : schedules.length === 0 ? (
          <EmptyState message="No schedules configured - Scout falls back to the default interval." />
        ) : (
          <ul className="recipient-list">
            {schedules.map((schedule) => (
              <li key={schedule.id} className={`recipient-list-item${schedule.enabled ? "" : " is-off"}`}>
                <div className="recipient-list-item-header">
                  <div>
                    <strong>
                      {schedule.frequency} at {schedule.time}
                    </strong>
                    <p className="recipient-summary">
                      {schedule.target_company_ids.length === 0
                        ? "All companies"
                        : `${schedule.target_company_ids.length} target compan${
                            schedule.target_company_ids.length === 1 ? "y" : "ies"
                          }`}
                    </p>
                  </div>
                  <Badge
                    label={schedule.enabled ? "enabled" : "disabled"}
                    variant={schedule.enabled ? "success" : "neutral"}
                  />
                </div>
                <div className="recipient-actions">
                  <button
                    type="button"
                    onClick={() =>
                      schedule.enabled ? disableSchedule.mutate(schedule.id) : enableSchedule.mutate(schedule.id)
                    }
                    disabled={enableSchedule.isPending || disableSchedule.isPending}
                  >
                    {schedule.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    type="button"
                    className="company-remove-button"
                    onClick={() => handleDeleteSchedule(schedule)}
                    disabled={deleteSchedule.isPending}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- recipients --------------------------------------------------- */}
      <section className="admin-panel" id="recipients" aria-label="Recipients">
        <div className="admin-panel-head">
          <div>
            <h2>Recipients</h2>
            <p className="admin-hint">Who receives generated reports, on what cadence, and through which channel.</p>
          </div>
          <button type="button" onClick={() => setIsFormOpen((open) => !open)}>
            {isFormOpen ? "Cancel" : "Add recipient"}
          </button>
        </div>

        {isFormOpen && (
          <form onSubmit={handleSubmit} className="add-recipient-form">
            <label htmlFor="recipient-name">Name</label>
            <input id="recipient-name" value={name} onChange={(event) => setName(event.target.value)} required />
            <label htmlFor="recipient-email">Email</label>
            <input
              id="recipient-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <label htmlFor="recipient-frequency">Preferred frequency</label>
            <select id="recipient-frequency" value={frequency} onChange={(event) => setFrequency(event.target.value)}>
              {FREQUENCY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <fieldset>
              <legend>Preferred channels</legend>
              {CHANNEL_OPTIONS.map((channel) => (
                <label key={channel} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={channels.includes(channel)}
                    onChange={() => setChannels((current) => toggleInList(current, channel))}
                  />
                  {channel}
                </label>
              ))}
            </fieldset>
            {createRecipient.isError && <p className="form-error">{getErrorMessage(createRecipient.error)}</p>}
            <button type="submit" disabled={createRecipient.isPending}>
              {createRecipient.isPending ? "Adding..." : "Add recipient"}
            </button>
          </form>
        )}

        {actionError && <p className="form-error">{actionError}</p>}

        {recipientsQuery.isLoading ? (
          <LoadingState />
        ) : recipientsQuery.isError ? (
          <ErrorState message={getErrorMessage(recipientsQuery.error)} />
        ) : recipients.length === 0 ? (
          <EmptyState message="No recipients added yet." />
        ) : (
          <ul className="recipient-list">
            {recipients.map((recipient) => (
              <li
                key={recipient.id}
                className={`recipient-list-item${recipient.delivery_status === "disabled" ? " is-off" : ""}`}
              >
                <div className="recipient-list-item-header">
                  <div>
                    <strong>{recipient.name}</strong>
                    <p className="recipient-summary">
                      {recipient.email} &middot; {recipient.preferred_frequency ?? "no frequency set"} &middot;{" "}
                      {recipient.preferred_channels.length > 0
                        ? recipient.preferred_channels.join(", ")
                        : "no channel set"}{" "}
                      &middot;{" "}
                      {recipient.preferred_company_ids.length === 0
                        ? "all companies"
                        : `${recipient.preferred_company_ids.length} compan${
                            recipient.preferred_company_ids.length === 1 ? "y" : "ies"
                          }`}
                    </p>
                  </div>
                  <Badge
                    label={recipient.delivery_status ?? "enabled"}
                    variant={recipient.delivery_status === "disabled" ? "neutral" : "success"}
                  />
                </div>

                {editingRecipientId === recipient.id ? (
                  <RecipientPreferencesForm
                    recipient={recipient}
                    isSaving={updatePreferences.isPending}
                    onCancel={() => setEditingRecipientId(null)}
                    onSave={(input) =>
                      updatePreferences.mutate(
                        { recipientId: recipient.id, input },
                        { onSuccess: () => setEditingRecipientId(null) },
                      )
                    }
                  />
                ) : (
                  <div className="recipient-actions">
                    <button type="button" onClick={() => setEditingRecipientId(recipient.id)}>
                      Edit preferences
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        recipient.delivery_status === "disabled"
                          ? enableRecipient.mutate(recipient.id)
                          : disableRecipient.mutate(recipient.id)
                      }
                      disabled={enableRecipient.isPending || disableRecipient.isPending}
                    >
                      {recipient.delivery_status === "disabled" ? "Enable" : "Disable"}
                    </button>
                    <button
                      type="button"
                      className="company-remove-button"
                      onClick={() => handleRemove(recipient)}
                      disabled={removeRecipient.isPending}
                    >
                      Remove
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- monitoring scope --------------------------------------------- */}
      <section className="admin-panel" aria-label="Monitoring scope">
        <div className="admin-panel-head">
          <div>
            <h2>Monitoring scope</h2>
            <p className="admin-hint">
              Which companies Scout tracks. Companies are added and archived from the Companies page.
            </p>
          </div>
          <Link to="/companies" className="admin-link-button">
            Manage companies
          </Link>
        </div>

        {companiesQuery.isLoading ? (
          <LoadingState />
        ) : companiesQuery.isError ? (
          <ErrorState message={getErrorMessage(companiesQuery.error)} />
        ) : (
          <>
            <dl className="admin-facts">
              <div className="admin-fact">
                <dt>Monitored</dt>
                <dd>{monitored.length}</dd>
              </div>
              <div className="admin-fact">
                <dt>Archived</dt>
                <dd>{archived.length}</dd>
              </div>
            </dl>
            {monitored.length > 0 && (
              <p className="admin-scope-list">{monitored.map((company) => company.name).join(", ")}</p>
            )}
          </>
        )}
      </section>

      {/* --- automation behavior ------------------------------------------ */}
      <section className="admin-panel" aria-label="Automation behaviour">
        <div className="admin-panel-head">
          <div>
            <h2>Automation behaviour</h2>
            <p className="admin-hint">
              How Scout is allowed to act. These come from the deployment environment and cannot be changed from
              this page.
            </p>
          </div>
        </div>

        {statusQuery.isLoading ? (
          <LoadingState />
        ) : statusQuery.isError ? (
          <ErrorState message={getErrorMessage(statusQuery.error)} />
        ) : status ? (
          <dl className="admin-facts admin-facts-wide">
            <div className="admin-fact">
              <dt>Environment</dt>
              <dd className="admin-fact-text">{status.delivery.environment}</dd>
            </div>
            <div className="admin-fact">
              <dt>Delivery</dt>
              <dd>
                <Badge
                  label={status.delivery.dry_run ? "Dry run" : "Live"}
                  variant={status.delivery.dry_run ? "neutral" : "warning"}
                />
              </dd>
            </div>
            <div className="admin-fact">
              <dt>Email</dt>
              <dd>
                <Badge
                  label={status.delivery.email_live ? "Live" : status.delivery.smtp_configured ? "Configured, off" : "Not configured"}
                  variant={status.delivery.email_live ? "success" : "neutral"}
                />
              </dd>
            </div>
            <div className="admin-fact">
              <dt>Teams</dt>
              <dd>
                <Badge
                  label={status.delivery.teams_live ? "Live" : status.delivery.teams_configured ? "Configured, off" : "Not configured"}
                  variant={status.delivery.teams_live ? "success" : "neutral"}
                />
              </dd>
            </div>
            <div className="admin-fact">
              <dt>Scheduler</dt>
              <dd>
                <Badge
                  label={status.scheduler.running ? "Running" : "Stopped"}
                  variant={status.scheduler.running ? "success" : "danger"}
                />
              </dd>
            </div>
            <div className="admin-fact">
              <dt>Fallback interval</dt>
              <dd className="admin-fact-text">{status.scheduler.interval_hours}h</dd>
            </div>
          </dl>
        ) : null}
      </section>
    </div>
  );
}

// Administration hub (V2->V3 parity pass). Recipients section reuses
// V2's full recipient CRUD (backend/routers/recipients.py) unchanged -
// no new backend work. Scheduling section drives the new /schedules/*
// endpoints (backend/routers/schedule.py), which read/write the
// Schedule entity that existed since V2 Phase 2 but was never wired
// into the live scheduler until now (backend/scheduler.py). Recipient
// preferences (channels/companies) already double as distribution
// configuration - who gets a report, and how - so there's no separate
// "distribution config" section here.
import { useState, type FormEvent } from "react";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
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

export function AdministrationPage() {
  const { confirm, confirmDialog } = useConfirm();
  const recipientsQuery = useRecipients();
  const { createRecipient, updatePreferences, enableRecipient, disableRecipient, removeRecipient } =
    useRecipientActions();

  const schedulesQuery = useSchedules();
  const { createSchedule, enableSchedule, disableSchedule, deleteSchedule } = useScheduleActions();
  const [isScheduleFormOpen, setIsScheduleFormOpen] = useState(false);
  const [scheduleActionError, setScheduleActionError] = useState<string | null>(null);

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

  return (
    <div className="administration-page">
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}
      <h1>Administration</h1>

      <Card title="Recipients">
        <div className="page-header">
          <p className="card-description">Who receives generated reports, and how.</p>
          <button type="button" onClick={() => setIsFormOpen((open) => !open)}>
            {isFormOpen ? "Cancel" : "Add Recipient"}
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
              <li key={recipient.id} className="recipient-list-item">
                <div className="recipient-list-item-header">
                  <div>
                    <strong>{recipient.name}</strong>
                    <p className="recipient-summary">
                      {recipient.email} - {recipient.preferred_frequency ?? "no frequency set"}
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
      </Card>

      <Card title="Scheduling">
        <div className="page-header">
          <p className="card-description">
            When Scout runs its research workflow automatically, instead of relying only on the .env-configured
            fallback interval.
          </p>
          <button type="button" onClick={() => setIsScheduleFormOpen((open) => !open)}>
            {isScheduleFormOpen ? "Cancel" : "Add Schedule"}
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
          <EmptyState message="No schedules configured yet - Scout falls back to the default interval." />
        ) : (
          <ul className="recipient-list">
            {schedules.map((schedule) => (
              <li key={schedule.id} className="recipient-list-item">
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
                  <Badge label={schedule.enabled ? "enabled" : "disabled"} variant={schedule.enabled ? "success" : "neutral"} />
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
      </Card>
    </div>
  );
}

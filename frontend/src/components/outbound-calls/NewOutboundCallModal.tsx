'use client';

import { createOutboundCallAtom, createOutboundCallFromFileAtom } from '@/atoms/OutboundCallsAtom';
import {
  CheckboxField,
  CustomButton,
  CustomModal,
  DateTimePicker,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import AdvancedDirectoryConfig from '@/components/contacts/shared/AdvancedDirectoryConfig';
import ContactFileInput from '@/components/contacts/shared/ContactFileInput';
import SampleDownloadMenu from '@/components/contacts/shared/SampleDownloadMenu';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { useSchema, useSchemasList } from '@/lib/api/contactSchemas';
import { listAgents } from '@/services/agentsService';
import { getChannelsByType, listChannelPhoneNumbers } from '@/services/channelService';
import { getOrganizationSettings } from '@/services/organizationService';
import { getOutboundConcurrencyMax } from '@/services/outboundCallService';
import type {
  CreateOutboundCallPayload,
  CreateOutboundCallResponse,
  OutboundTriggerProvider,
} from '@/types/outboundCall';
import { getBrowserTimeZone, getTimeZoneAbbreviation } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useSetAtom } from 'jotai';
import { AlertTriangle, Upload } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';

interface Option {
  value: string;
  label: string;
}

interface OutboundCallForm {
  agent_id: string;
  from_number: string;
  to_numbers_text: string;
  schedule: boolean;
  scheduled_at: string;
  provider: OutboundTriggerProvider;
}

// How the call is triggered. Twilio places a real PSTN call; WebSocket bridges the
// call over a WebSocket to a remote /ws/test (agent-to-agent, no telephony).
const TRIGGER_PROVIDER_OPTIONS: { value: OutboundTriggerProvider; label: string }[] = [
  { value: 'twilio', label: 'Twilio (phone call)' },
  { value: 'websocket', label: 'WebSocket (test bridge)' },
];

interface NewOutboundCallModalProps {
  open: boolean;
  onClose: () => void;
  /** Pre-select (and lock) an agent — used by the "Make Call" action on the agents page. */
  defaultAgentId?: string;
  lockAgent?: boolean;
  /** Called after call(s) are queued. Lets the Scheduled Calls page refresh in place
   *  instead of navigating. When omitted, queued calls navigate to the list. */
  onScheduled?: () => void;
}

// Sentinel for the "let the backend pick a number" option. Radix Select forbids an
// empty-string item value, so we use a non-empty sentinel and drop it on submit.
const AUTO_FROM_NUMBER = '__auto__';

/** Parse a free-text / CSV blob into a de-duplicated list of E.164 destination numbers.
 *  - Splits on newlines, commas and semicolons; strips spaces/dashes/parens/dots.
 *  - Skips non-numeric tokens (so CSV headers like `phone_number` are ignored).
 *  - Adds a leading `+` when missing (assumes the country code is present).
 *  The backend still does the authoritative E.164 validation and reports any it rejects. */
function parseNumbers(text: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of (text || '').split(/[\n,;]+/)) {
    const cleaned = raw.trim().replace(/[\s\-().]/g, '');
    if (!cleaned) continue;
    // Phone-like only: optional single leading + then 7–15 digits. Drops headers/labels.
    if (!/^\+?\d{7,15}$/.test(cleaned)) continue;
    const e164 = cleaned.startsWith('+') ? cleaned : `+${cleaned}`;
    if (!seen.has(e164)) {
      seen.add(e164);
      out.push(e164);
    }
  }
  return out;
}

export default function NewOutboundCallModal({
  open,
  onClose,
  defaultAgentId,
  lockAgent = false,
  onScheduled,
}: NewOutboundCallModalProps) {
  const router = useRouter();
  const createCall = useSetAtom(createOutboundCallAtom);
  const createCallFromFile = useSetAtom(createOutboundCallFromFileAtom);

  const { control, handleSubmit, watch, reset, setValue } = useForm<OutboundCallForm>({
    defaultValues: {
      agent_id: defaultAgentId ?? '',
      from_number: AUTO_FROM_NUMBER,
      to_numbers_text: '',
      schedule: false,
      scheduled_at: '',
      provider: 'twilio',
    },
  });

  const [agentOptions, setAgentOptions] = useState<Option[]>([]);
  const [fromOptions, setFromOptions] = useState<Option[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  // The org's default scheduling timezone (settings JSONB); seeds the picker.
  const [orgTz, setOrgTz] = useState<string>('');
  // The timezone the user last applied in the picker — drives the tz label + default.
  const [scheduledTz, setScheduledTz] = useState<string>('');
  // Numbers the backend rejected on the last submit (listed so the user can fix them).
  const [invalidNumbers, setInvalidNumbers] = useState<{ to_number: string; error: string }[]>([]);
  // A chosen CSV/Excel file — parsed SERVER-SIDE (never read in the browser).
  const [csvFile, setCsvFile] = useState<File | null>(null);
  // Upload mode: switches the "To numbers" area from the manual textarea to the
  // schema + file + directory upload panel (like the contacts Upload modal).
  const [uploadMode, setUploadMode] = useState(false);
  const [schemaId, setSchemaId] = useState<string>('');
  const [pickedDirectoryId, setPickedDirectoryId] = useState<string>('');

  // Schema + directory pickers for the upload path (mirrors the contacts Upload modal): the
  // schema drives the downloadable sample; the directory (default "Global") is where the
  // uploaded contacts are created + assigned. Only fetched for the upload path — a user who
  // just types numbers manually never triggers these list queries (matches the sibling
  // UploadContactsModal, which gates its list too).
  const { data: schemasPage } = useSchemasList({ page_size: 100 }, { enabled: open && uploadMode });
  const { data: directoriesPage } = useDirectoriesList(
    { page_size: 100 },
    { enabled: open && uploadMode },
  );
  const schemaOptions = (schemasPage?.data ?? []).map((s) => ({ value: s.id, label: s.name }));
  const directoryOptions = (directoriesPage?.data ?? []).map((d) => ({
    value: d.id,
    label: d.name,
  }));
  const globalDirectory = directoriesPage?.data?.find((d) => d.name === 'Global');
  // Optional file column holding each row's OWN call time (parsed with the schema's datetime
  // field format/timezone). When set, per-row times override the single "Schedule for later".
  const [scheduleColumn, setScheduleColumn] = useState<string>('');
  // Per-batch concurrency: how many of THIS batch's calls dial at once. `concurrencyMax` is the
  // env ceiling the field is capped to + defaults to (null = no upper bound); `concurrencyValue`
  // is the user's choice, sent with the request (empty → the backend applies the env default).
  const [concurrencyMax, setConcurrencyMax] = useState<number | null>(null);
  const [concurrencyValue, setConcurrencyValue] = useState<number | null>(null);
  // Whether this user may use the WebSocket trigger (backend env allowlist). Default false so the
  // "Trigger via" selector stays hidden until the capabilities call confirms access.
  const [wsTriggerAllowed, setWsTriggerAllowed] = useState<boolean>(false);

  const { data: schemaDetail } = useSchema(schemaId || null);

  const scheduleOn = watch('schedule');
  const scheduledAtValue = watch('scheduled_at');
  const numbersText = watch('to_numbers_text');
  const numberCount = useMemo(() => parseNumbers(numbersText).length, [numbersText]);
  const browserTz = useMemo(() => getBrowserTimeZone(), []);
  // Default zone for the schedule picker: the org's configured zone, else the browser's.
  const defaultTz = orgTz || browserTz;
  const effectiveTz = scheduledTz || defaultTz;

  // From-number options with a leading "auto" entry — leaving it on lets the backend
  // pick the org's configured number (single → that one; multiple → round-robin).
  const fromSelectOptions = useMemo<Option[]>(
    () => [{ value: AUTO_FROM_NUMBER, label: 'Auto — use configured number(s)' }, ...fromOptions],
    [fromOptions],
  );

  useEffect(() => {
    if (!open) return;
    reset({
      agent_id: defaultAgentId ?? '',
      from_number: AUTO_FROM_NUMBER,
      to_numbers_text: '',
      schedule: false,
      scheduled_at: '',
      provider: 'twilio',
    });
    setInvalidNumbers([]);
    setScheduledTz('');
    setCsvFile(null);
    setUploadMode(false);
    setSchemaId('');
    setPickedDirectoryId('');
    setScheduleColumn('');

    let active = true;
    setOptionsLoading(true);
    (async () => {
      try {
        const [agents, channels, settings] = await Promise.all([
          listAgents({ page_size: 200 }),
          getChannelsByType('twilio'),
          getOrganizationSettings().catch(() => ({})),
        ]);
        if (!active) return;

        const tz = (settings as Record<string, unknown>)?.scheduling_timezone;
        if (typeof tz === 'string' && tz) setOrgTz(tz);

        setAgentOptions(
          (agents.items ?? [])
            .filter((a) => a.agent_type === 'outbound' || a.agent_type === 'both')
            .map((a) => ({ value: a.id, label: a.name })),
        );

        const numbersNested = await Promise.all(
          (channels ?? []).map((c) => listChannelPhoneNumbers(c.id).catch(() => [])),
        );
        if (!active) return;
        setFromOptions(
          numbersNested.flat().map((n) => ({
            value: n.number,
            label: n.label ? `${n.number} (${n.label})` : n.number,
          })),
        );
      } catch (err) {
        handleApiError(err);
      } finally {
        if (active) setOptionsLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [open, defaultAgentId, reset]);

  // When "Schedule for later" is turned on, default the time to the current instant (shown
  // as the current wall-clock time in the selected timezone) so the field isn't empty.
  useEffect(() => {
    if (scheduleOn && !scheduledAtValue) {
      setValue('scheduled_at', new Date().toISOString());
    }
  }, [scheduleOn, scheduledAtValue, setValue]);

  // Default the target directory to the org's "Global" directory (like the Upload modal)
  // once directories load and the user hasn't picked another.
  useEffect(() => {
    if (open && !pickedDirectoryId && globalDirectory) {
      setPickedDirectoryId(globalDirectory.id);
    }
  }, [open, pickedDirectoryId, globalDirectory]);

  // Load the env ceiling so the per-batch "Concurrent calls" field can cap + default to it.
  useEffect(() => {
    if (!open) return;
    let active = true;
    getOutboundConcurrencyMax()
      .then((c) => {
        if (!active) return;
        setConcurrencyMax(c.max);
        setConcurrencyValue(c.max); // default the batch to the env max (user can lower it)
        setWsTriggerAllowed(!!c.ws_trigger_allowed);
      })
      .catch(() => {
        if (!active) return;
        setConcurrencyMax(null);
        setWsTriggerAllowed(false);
      });
    return () => {
      active = false;
    };
  }, [open]);

  const onSubmit = useCallback(
    async (values: OutboundCallForm) => {
      const usingFile = uploadMode;
      const numbers = usingFile ? [] : parseNumbers(values.to_numbers_text);
      if (usingFile && !csvFile) {
        showToast.error('Choose a CSV or Excel file to upload');
        return;
      }
      if (!usingFile && !numbers.length) {
        showToast.error('Add at least one destination number or upload a file');
        return;
      }
      setSubmitting(true);
      setInvalidNumbers([]);
      try {
        // Per-batch concurrency for THIS submission (empty → backend applies the env default).
        const maxConcurrency = concurrencyValue && concurrencyValue > 0 ? concurrencyValue : null;
        const scheduled = values.schedule && values.scheduled_at;
        // Omit from_number when left on "Auto" so the backend selects one.
        const fromNumber =
          values.from_number && values.from_number !== AUTO_FROM_NUMBER
            ? values.from_number
            : undefined;
        // DateTimePicker already emits a UTC ISO instant, so use it as-is.
        const scheduledAt = scheduled ? values.scheduled_at : null;

        let res: CreateOutboundCallResponse;
        if (usingFile && csvFile) {
          // File path: contacts are parsed SERVER-SIDE (never read in the browser) and
          // created in the selected directory (default "Global"), then scheduled.
          const fd = new FormData();
          fd.append('agent_id', values.agent_id);
          if (fromNumber) fd.append('from_number', fromNumber);
          if (scheduledAt) fd.append('scheduled_at', scheduledAt);
          if (pickedDirectoryId) fd.append('directory_id', pickedDirectoryId);
          if (schemaId) fd.append('schema_id', schemaId);
          if (scheduleColumn.trim()) fd.append('schedule_column', scheduleColumn.trim());
          if (maxConcurrency) fd.append('max_concurrency', String(maxConcurrency));
          fd.append('provider', values.provider);
          fd.append('file', csvFile);
          res = await createCallFromFile(fd);
        } else {
          const payload: CreateOutboundCallPayload = {
            agent_id: values.agent_id,
            from_number: fromNumber,
            to_numbers: numbers,
            scheduled_at: scheduledAt,
            directory_id: pickedDirectoryId || undefined,
            max_concurrency: maxConcurrency ?? undefined,
            provider: values.provider,
          };
          res = await createCall(payload);
        }
        if (res?.invalid?.length) {
          setInvalidNumbers(res.invalid);
          showToast.warning(
            `${res.invalid.length} row(s) skipped`,
            'See the reasons listed in the form (invalid number, or an unusable/past schedule time).',
          );
        }
        onClose();
        // parallel_websocket (immediate WS test-bridge fan-out) dials right away, same as immediate.
        if (res?.mode === 'immediate' || res?.mode === 'parallel_websocket') {
          showToast.success('Calling now', 'The call will appear in Call History.');
          router.push('/call-history');
        } else {
          showToast.success(
            res?.mode === 'bulk' ? `${res.count} calls queued` : 'Call scheduled',
            'Track them on the agent’s Schedule tab.',
          );
          // The Schedule view always passes onScheduled to refresh in place; there is no
          // global scheduled-calls route to navigate to anymore.
          onScheduled?.();
        }
      } catch (err) {
        // Keep the modal open so the user can correct + retry (error-recovery).
        handleApiError(err);
      } finally {
        setSubmitting(false);
      }
    },
    [
      uploadMode,
      csvFile,
      pickedDirectoryId,
      schemaId,
      scheduleColumn,
      concurrencyValue,
      createCall,
      createCallFromFile,
      onClose,
      onScheduled,
      router,
    ],
  );

  // Intimate the user when the current settings would place calls IMMEDIATELY instead of
  // scheduling them. In upload mode a row dials now whenever it has no future time: with
  // "Schedule for later" off there is no fallback, so an empty schedule column (or empty
  // cells within it) means an immediate call. Manual "Call now" is already explicit.
  const immediateNotice = useMemo(() => {
    if (!uploadMode || scheduleOn) return null;
    const col = scheduleColumn.trim();
    return col
      ? `Contacts whose “${col}” cell is empty will be called immediately (rows with a valid future time are scheduled). Turn on “Schedule for later” to give the rest a fallback time.`
      : 'Every contact in the file will be called immediately. Name a “Schedule column” above to use per-row times, or turn on “Schedule for later”.';
  }, [uploadMode, scheduleOn, scheduleColumn]);

  // In upload mode the action is "scheduling" whenever a time source exists — either the
  // "Schedule for later" fallback or a per-row schedule column — so the button should read
  // "Schedule call" rather than "Call … now" (only a bare upload with neither dials now).
  const uploadSchedules = uploadMode && (scheduleOn || !!scheduleColumn.trim());
  const submitLabel = uploadMode
    ? uploadSchedules
      ? 'Schedule call'
      : 'Call from file now'
    : scheduleOn
      ? numberCount > 1
        ? `Schedule ${numberCount} calls`
        : 'Schedule call'
      : numberCount > 1
        ? `Call ${numberCount} numbers`
        : 'Call now';

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="New outbound call"
      width="sm:max-w-2xl"
      footer={
        <>
          <CustomButton type="default" onClick={onClose} disabled={submitting}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            loading={submitting}
            disabled={uploadMode ? !csvFile : numberCount === 0}
            onClick={handleSubmit(onSubmit)}
          >
            {submitLabel}
          </CustomButton>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <SelectInput
          name="agent_id"
          control={control}
          rules={{ required: 'Select an agent' }}
          label="Agent"
          isRequired
          placeholder="Select an outbound agent"
          loading={optionsLoading}
          disabled={lockAgent}
          options={agentOptions}
        />
        <SelectInput
          name="from_number"
          control={control}
          label="From number (optional)"
          placeholder="Auto — use configured number(s)"
          loading={optionsLoading}
          options={fromSelectOptions}
        />
        {/* Trigger selector shown only to allowlisted users (WS is an internal test tool);
            everyone else stays on the default Twilio provider with no selector. */}
        {wsTriggerAllowed && (
          <SelectInput
            name="provider"
            control={control}
            label="Trigger via"
            options={TRIGGER_PROVIDER_OPTIONS}
          />
        )}

        {/* Per-batch concurrency — capped to the env max when one is configured. */}
        <TextInput
          label="Concurrent calls"
          type="number"
          min={1}
          max={concurrencyMax ?? undefined}
          value={concurrencyValue ?? ''}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === '') {
              setConcurrencyValue(null);
              return;
            }
            const n = parseInt(raw, 10);
            if (Number.isNaN(n)) {
              setConcurrencyValue(null);
              return;
            }
            const bounded = concurrencyMax !== null ? Math.min(concurrencyMax, n) : n;
            setConcurrencyValue(Math.max(1, bounded));
          }}
          helperText={
            concurrencyMax !== null
              ? `How many of this batch's calls dial at once (max ${concurrencyMax}). The next fires as one finishes.`
              : "How many of this batch's calls dial at once. Leave empty for no limit. The next fires as one finishes."
          }
        />

        {/* Mapping schema — drives the downloadable sample template (always visible). */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-foreground">Mapping schema</span>
            {schemaId && schemaDetail ? (
              <SampleDownloadMenu schemaId={schemaId} schemaName={schemaDetail.name} />
            ) : null}
          </div>
          <SelectInput
            name="upload-schema"
            options={schemaOptions}
            value={schemaId}
            onValueChange={setSchemaId}
            placeholder="Select a schema to download a sample"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              To numbers <span className="text-destructive">*</span>
            </span>
            {uploadMode ? (
              <CustomButton
                type="text"
                onClick={() => {
                  setUploadMode(false);
                  setCsvFile(null);
                  setScheduleColumn('');
                }}
              >
                Enter numbers manually
              </CustomButton>
            ) : (
              <CustomButton
                type="text"
                icon={<Upload className="size-3.5" />}
                onClick={() => setUploadMode(true)}
              >
                Upload CSV/Excel
              </CustomButton>
            )}
          </div>
          {uploadMode ? (
            <>
              <ContactFileInput
                label="Contact file"
                accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                allowedExtensions={['.csv', '.xlsx']}
                value={csvFile}
                onChange={setCsvFile}
                hint="Upload a CSV or .xlsx (matching the selected schema — download the sample above). It is parsed on the server; the file needs a phone_number column."
              />
              <TextInput
                label="Schedule column (optional)"
                placeholder="e.g. date_time"
                value={scheduleColumn}
                onChange={(e) => setScheduleColumn(e.target.value)}
                helperText="Name the file column holding each row's call time. It's parsed with the selected schema's date/datetime field format and overrides 'Schedule for later' per row. Rows with a blank cell use the time below; unparseable or past times are skipped."
              />
            </>
          ) : (
            <>
              <TextAreaField
                name="to_numbers_text"
                control={control}
                rows={4}
                placeholder="+14155550123, +14155550124, …comma-separated, or paste"
              />
              <p className="text-xs text-muted-foreground">
                {numberCount > 0
                  ? `${numberCount} number${numberCount > 1 ? 's' : ''} — E.164 format (e.g. +14155550123). Multiple comma- or line-separated numbers are queued and shown on Scheduled Calls.`
                  : 'Enter E.164 numbers (e.g. +14155550123), separated by commas or new lines, or upload a CSV/Excel file.'}
              </p>
            </>
          )}
          {invalidNumbers.length > 0 && (
            <div
              role="alert"
              className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800 ring-1 ring-inset ring-red-200"
            >
              <p className="font-medium">
                {invalidNumbers.length} row{invalidNumbers.length > 1 ? 's were' : ' was'} skipped:
              </p>
              <ul className="mt-1 list-disc pl-4">
                {invalidNumbers.map((n, i) => (
                  <li key={`${n.to_number}-${i}`} className="truncate">
                    <span className="font-medium">{n.to_number}</span>
                    {n.error ? ` — ${n.error}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {immediateNotice && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 ring-1 ring-inset ring-amber-200"
          >
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
            <span>{immediateNotice}</span>
          </div>
        )}
        <CheckboxField id="schedule" control={control} label="Schedule for later" />
        {scheduleOn && (
          <Controller
            name="scheduled_at"
            control={control}
            rules={{
              required: 'Pick a date & time',
              // Allow "now" (default) — the backend keeps a 60s grace and dials ASAP for
              // near-now times; only a clearly past time is rejected.
              validate: (v: string) =>
                (!!v && new Date(v).getTime() > Date.now() - 60_000) ||
                'Pick a time that is not in the past',
            }}
            render={({ field, fieldState }) => (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">
                  Scheduled time <span className="text-destructive">*</span>
                </label>
                <DateTimePicker
                  value={{ value: field.value || null, timeZone: effectiveTz }}
                  onChange={(v) => {
                    field.onChange(v.value ?? '');
                    if (v.timeZone) setScheduledTz(v.timeZone);
                  }}
                  placeholder="Pick a date & time"
                />
                <p className="text-xs text-muted-foreground">
                  Timezone: {effectiveTz}
                  {getTimeZoneAbbreviation(effectiveTz, field.value || undefined)
                    ? ` (${getTimeZoneAbbreviation(effectiveTz, field.value || undefined)})`
                    : ''}
                </p>
                {fieldState.error && (
                  <span className="text-xs text-destructive">{fieldState.error.message}</span>
                )}
              </div>
            )}
          />
        )}

        {/* Directory the created contacts land in — defaults to "Global", tucked behind the
            same "Advanced configuration" disclosure the Upload modal uses. Kept last. */}
        <AdvancedDirectoryConfig
          options={directoryOptions}
          value={pickedDirectoryId}
          onChange={setPickedDirectoryId}
          loading={!directoriesPage}
        />
      </form>
    </CustomModal>
  );
}

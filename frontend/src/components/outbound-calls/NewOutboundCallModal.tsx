'use client';

import { createOutboundCallAtom } from '@/atoms/OutboundCallsAtom';
import {
  CheckboxField,
  CustomButton,
  CustomModal,
  DateTimePicker,
  SelectInput,
  TextAreaField,
} from '@/components/shared';
import { listAgents } from '@/services/agentsService';
import { getChannelsByType, listChannelPhoneNumbers } from '@/services/channelService';
import type { CreateOutboundCallPayload } from '@/types/outboundCall';
import { getBrowserTimeZone } from '@/utils/date';
import { triggerCsvDownload } from '@/utils/download';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useSetAtom } from 'jotai';
import { Download, Upload } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
}

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

// datetime-local (local wall-clock) → ISO string the backend parses as a future instant.
const toIso = (local: string): string => new Date(local).toISOString();

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
  const fileRef = useRef<HTMLInputElement>(null);

  const { control, handleSubmit, watch, reset, setValue, getValues } = useForm<OutboundCallForm>({
    defaultValues: {
      agent_id: defaultAgentId ?? '',
      from_number: '',
      to_numbers_text: '',
      schedule: false,
      scheduled_at: '',
    },
  });

  const [agentOptions, setAgentOptions] = useState<Option[]>([]);
  const [fromOptions, setFromOptions] = useState<Option[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const scheduleOn = watch('schedule');
  const numbersText = watch('to_numbers_text');
  const numberCount = useMemo(() => parseNumbers(numbersText).length, [numbersText]);
  const browserTz = useMemo(() => getBrowserTimeZone(), []);

  useEffect(() => {
    if (!open) return;
    reset({
      agent_id: defaultAgentId ?? '',
      from_number: '',
      to_numbers_text: '',
      schedule: false,
      scheduled_at: '',
    });

    let active = true;
    setOptionsLoading(true);
    (async () => {
      try {
        const [agents, channels] = await Promise.all([
          listAgents({ page_size: 200 }),
          getChannelsByType('twilio'),
        ]);
        if (!active) return;

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

  const onCsvSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = ''; // allow re-selecting the same file
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = parseNumbers(text);
        if (!parsed.length) {
          showToast.warning('No numbers found', 'The CSV had no recognizable phone numbers.');
          return;
        }
        const existing = parseNumbers(getValues('to_numbers_text'));
        const merged = Array.from(new Set([...existing, ...parsed]));
        setValue('to_numbers_text', merged.join('\n'), { shouldValidate: true });
        showToast.success(`${parsed.length} number(s) imported`);
      } catch {
        showToast.error('Could not read the CSV file');
      }
    },
    [getValues, setValue],
  );

  const onSubmit = useCallback(
    async (values: OutboundCallForm) => {
      const numbers = parseNumbers(values.to_numbers_text);
      if (!numbers.length) {
        showToast.error('Add at least one destination number');
        return;
      }
      setSubmitting(true);
      try {
        const scheduled = values.schedule && values.scheduled_at;
        const payload: CreateOutboundCallPayload = {
          agent_id: values.agent_id,
          from_number: values.from_number,
          to_numbers: numbers,
          scheduled_at: scheduled ? toIso(values.scheduled_at) : null,
        };
        const res = await createCall(payload);
        if (res?.invalid?.length) {
          showToast.warning(
            `${res.invalid.length} number(s) skipped`,
            'They were not valid E.164.',
          );
        }
        onClose();
        if (res?.mode === 'immediate') {
          showToast.success('Calling now', 'The call will appear in Call History.');
          router.push('/call-history');
        } else {
          showToast.success(
            res?.mode === 'bulk' ? `${res.count} calls queued` : 'Call scheduled',
            'Track them on the Scheduled Calls page.',
          );
          if (onScheduled) onScheduled();
          else router.push('/scheduled-calls');
        }
      } catch (err) {
        // Keep the modal open so the user can correct + retry (error-recovery).
        handleApiError(err);
      } finally {
        setSubmitting(false);
      }
    },
    [createCall, onClose, onScheduled, router],
  );

  const submitLabel = scheduleOn
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
      width="sm:max-w-md"
      footer={
        <>
          <CustomButton type="default" onClick={onClose} disabled={submitting}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            loading={submitting}
            disabled={numberCount === 0}
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
          rules={{ required: 'Select a from number' }}
          label="From number"
          isRequired
          placeholder="Select a Twilio number"
          loading={optionsLoading}
          options={fromOptions}
        />
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              To numbers <span className="text-destructive">*</span>
            </span>
            <div className="flex items-center gap-1">
              <CustomButton
                type="text"
                icon={<Download className="size-3.5" />}
                onClick={() =>
                  triggerCsvDownload(
                    'outbound-numbers-sample.csv',
                    ['phone_number', '+14155550123', '+14155550124', '+442071838750'].join('\n'),
                  )
                }
              >
                Sample CSV
              </CustomButton>
              <CustomButton
                type="text"
                icon={<Upload className="size-3.5" />}
                onClick={() => fileRef.current?.click()}
              >
                Import CSV
              </CustomButton>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv,text/plain"
              className="hidden"
              onChange={onCsvSelected}
            />
          </div>
          <TextAreaField
            name="to_numbers_text"
            control={control}
            rows={4}
            placeholder={'+14155550123\n+14155550124\n…one per line, or paste / import a CSV'}
            rules={{
              validate: (v: string) => parseNumbers(v).length > 0 || 'Add at least one number',
            }}
          />
          <p className="text-xs text-muted-foreground">
            {numberCount > 0
              ? `${numberCount} number${numberCount > 1 ? 's' : ''} — E.164 format (e.g. +14155550123). Multiple numbers are queued and shown on Scheduled Calls.`
              : 'Enter E.164 numbers (e.g. +14155550123), one per line, or import a CSV.'}
          </p>
        </div>
        <CheckboxField id="schedule" control={control} label="Schedule for later" />
        {scheduleOn && (
          <Controller
            name="scheduled_at"
            control={control}
            rules={{
              required: 'Pick a time in the future',
              validate: (v: string) =>
                (!!v && new Date(v).getTime() > Date.now()) || 'Pick a time in the future',
            }}
            render={({ field, fieldState }) => (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">
                  Scheduled time <span className="text-destructive">*</span>
                </label>
                <DateTimePicker
                  value={{ value: field.value || null, timeZone: browserTz }}
                  onChange={(v) => field.onChange(v.value ?? '')}
                  placeholder="Pick a date & time"
                />
                {fieldState.error && (
                  <span className="text-xs text-destructive">{fieldState.error.message}</span>
                )}
              </div>
            )}
          />
        )}
      </form>
    </CustomModal>
  );
}

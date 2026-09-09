'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import CustomModal from '@/components/shared/CustomModal';
import SelectInput from '@/components/shared/SelectInput';
import TextAreaField from '@/components/shared/TextAreaField';
import TextInput from '@/components/shared/TextInput';
import { PROFILE_VARIABLE_SOURCE_OPTIONS } from '@/constants/profileWebhook';
import type { AgentProfileVariable } from '@/types/agentProfileVariable';

/**
 * Client-side validation. Mirrors the backend rules in
 * `core/services/agents/agent_profile_variable_service.py` — the server
 * re-enforces the same limits, so this schema is UX-only (better inline
 * errors before submit). NEVER treat client validation as source of truth.
 */
const KEY_RE = /^[a-zA-Z][a-zA-Z0-9_]{0,63}$/;
const SOURCE_PATH_RE = /^[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*$/;
const MAX_VALUE_BYTES = 10_240;
const MAX_DESCRIPTION_LEN = 1000;
const MAX_SOURCE_PATH_LEN = 200;

const profileVarSchema = z
  .object({
    key: z
      .string()
      .trim()
      .min(1, 'Key is required.')
      .max(64, 'Key must be 64 characters or fewer.')
      .regex(KEY_RE, 'Use letters, numbers, or underscores; start with a letter.'),
    value: z
      .string()
      .max(MAX_VALUE_BYTES, `Value is too long (max ${MAX_VALUE_BYTES} characters).`)
      .refine(
        (v) => new TextEncoder().encode(v).length <= MAX_VALUE_BYTES,
        `Value is too long (max ${MAX_VALUE_BYTES} bytes).`,
      ),
    // Description is always a string at runtime (TextAreaField never emits
    // undefined). Empty string is treated as "no description" server-side, so
    // there's no need for `.optional().or(z.literal(''))` — that combo behaves
    // differently across zod versions and can leave the form spuriously
    // invalid on first mount. Simple `.max()` on a string covers every case.
    description: z
      .string()
      .max(MAX_DESCRIPTION_LEN, `Description must be ${MAX_DESCRIPTION_LEN} characters or fewer.`),
    source: z.enum(['static', 'webhook']),
    source_path: z.string().trim().max(MAX_SOURCE_PATH_LEN),
  })
  .superRefine((data, ctx) => {
    if (data.source !== 'webhook') return;
    if (!data.source_path) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['source_path'],
        message: 'A source path is required for a webhook variable.',
      });
    } else if (!SOURCE_PATH_RE.test(data.source_path)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['source_path'],
        message: "Use a dot-path like 'properties.name'.",
      });
    }
  });

export type ProfileVarFormValues = z.infer<typeof profileVarSchema>;

interface Props {
  open: boolean;
  onClose: () => void;
  /** Undefined = create; a row = edit that row. */
  initial?: AgentProfileVariable | null;
  onSubmit: (values: ProfileVarFormValues) => Promise<void> | void;
  submitting?: boolean;
}

const EMPTY: ProfileVarFormValues = {
  key: '',
  value: '',
  description: '',
  source: 'static',
  source_path: '',
};

export default function ProfileVariableModal({
  open,
  onClose,
  initial,
  onSubmit,
  submitting = false,
}: Props) {
  const isEdit = !!initial;
  const {
    control,
    handleSubmit,
    reset,
    formState: { isValid },
  } = useForm<ProfileVarFormValues>({
    resolver: zodResolver(profileVarSchema),
    defaultValues: EMPTY,
    mode: 'onChange',
  });

  const source = useWatch({ control, name: 'source' });
  const isWebhook = source === 'webhook';

  // Reset the form whenever the modal opens (or the target row changes) so a
  // second open doesn't leak stale values from the previous session.
  useEffect(() => {
    if (!open) return;
    reset(
      initial
        ? {
            key: initial.key,
            value: initial.value ?? '',
            description: initial.description ?? '',
            source: initial.source ?? 'static',
            source_path: initial.source_path ?? '',
          }
        : EMPTY,
    );
  }, [open, initial, reset]);

  const submit = handleSubmit(async (values) => {
    await onSubmit(values);
  });

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit profile variable' : 'Add profile variable'}
      description={
        isEdit
          ? 'Update this variable. Any {{profile.<key>}} references pick up the change on the next call.'
          : 'Define a value once, reference it as {{profile.<key>}} anywhere.'
      }
      confirmText={isEdit ? 'Save' : 'Add'}
      cancelText="Cancel"
      onConfirm={submit}
      confirmLoading={submitting}
      confirmDisabled={submitting || !isValid}
      width="520px"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex flex-col gap-3"
      >
        <TextInput
          name="key"
          control={control}
          label="Key"
          isRequired
          placeholder="e.g. customer_name"
          helperText="Letters, numbers, underscore. Referenced as {{profile.<key>}}."
          disabled={submitting}
        />
        <SelectInput
          name="source"
          control={control}
          label="Source"
          options={PROFILE_VARIABLE_SOURCE_OPTIONS}
          disabled={submitting}
        />
        {isWebhook && (
          <TextInput
            name="source_path"
            control={control}
            label="Source path"
            isRequired
            placeholder="e.g. properties.name"
            helperText="Dot-path into the webhook JSON response. The Value below is the fallback."
            disabled={submitting}
          />
        )}
        <TextAreaField
          name="value"
          control={control}
          label={isWebhook ? 'Fallback value' : 'Value'}
          rows={3}
          placeholder="e.g. Acme Corp"
          helperText={
            isWebhook
              ? 'Used when the webhook fails, times out, or the path does not resolve.'
              : 'Empty is allowed. Substituted verbatim into the prompt at call time.'
          }
          disabled={submitting}
        />
        <TextAreaField
          name="description"
          control={control}
          label="Description (optional)"
          rows={2}
          placeholder="What this variable represents — shown in the variable picker."
          disabled={submitting}
        />
      </form>
    </CustomModal>
  );
}

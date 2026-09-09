'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import RequestIdentifiersField from '@/components/agents/profile-variables/webhook/RequestIdentifiersField';
import WebhookDirectionsField from '@/components/agents/profile-variables/webhook/WebhookDirectionsField';
import WebhookHeadersField from '@/components/agents/profile-variables/webhook/WebhookHeadersField';
import WebhookTestPanel from '@/components/agents/profile-variables/webhook/WebhookTestPanel';
import {
  emptyWebhookForm,
  formValuesToUpsertInput,
  webhookToFormValues,
} from '@/components/agents/profile-variables/webhook/webhookConfigHelpers';
import {
  AppLoader,
  CheckboxField,
  CustomButton,
  CustomModal,
  SelectInput,
  TextInput,
} from '@/components/shared';
import { HTTP_METHOD_OPTIONS } from '@/constants/profileWebhook';
import {
  useAgentProfileWebhook,
  useDeleteAgentProfileWebhook,
  useUpsertAgentProfileWebhook,
} from '@/lib/api/agentProfileWebhook';
import { webhookConfigSchema, type WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/**
 * The per-agent webhook data source config (edit-mode only). Fills
 * webhook-sourced profile variables from the agent's endpoint at call start.
 */
export default function WebhookConfigSection({ agentId }: { agentId: string }) {
  const { data: config, isLoading } = useAgentProfileWebhook(agentId);
  const upsert = useUpsertAgentProfileWebhook(agentId);
  const del = useDeleteAgentProfileWebhook(agentId);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { isValid, isDirty, errors },
  } = useForm<WebhookConfigFormValues>({
    resolver: zodResolver(webhookConfigSchema),
    defaultValues: emptyWebhookForm(),
    mode: 'onChange',
  });

  const savedExists = !!config;

  useEffect(() => {
    if (isLoading) return;
    reset(webhookToFormValues(config ?? null));
  }, [isLoading, config, reset]);

  const submit = handleSubmit(async (values) => {
    try {
      await upsert.mutateAsync(formValuesToUpsertInput(values));
      showToast.success('Webhook saved.');
    } catch (err) {
      handleApiError(err);
    }
  });

  const runDelete = async () => {
    try {
      await del.mutateAsync();
      reset(emptyWebhookForm());
      setConfirmDelete(false);
      showToast.success('Webhook removed.');
    } catch (err) {
      handleApiError(err);
    }
  };

  if (isLoading) {
    return (
      <div className="py-6">
        <AppLoader />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <CheckboxField id="is_enabled" control={control} label="Enable webhook data source" />

      <TextInput
        name="endpoint_url"
        control={control}
        label="Endpoint URL"
        isRequired
        placeholder="https://api.example.com/lookup"
        helperText="HTTPS only. Called at call start with the caller's phone."
      />

      <SelectInput
        name="http_method"
        control={control}
        label="HTTP method"
        options={HTTP_METHOD_OPTIONS}
      />

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Custom headers</span>
        <WebhookHeadersField control={control} />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Send caller identifiers</span>
        <p className="text-xs text-muted-foreground">
          Which caller field to send, under what param name, and where.
        </p>
        <RequestIdentifiersField control={control} />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Run on</span>
        <WebhookDirectionsField control={control} errors={errors} />
      </div>

      <TextInput
        name="timeout_seconds"
        control={control}
        type="number"
        label="Timeout (seconds)"
        helperText="How long to wait before falling back to default values (1–30, default 3)."
      />

      <div className="flex items-center justify-between gap-2">
        {savedExists ? (
          <CustomButton
            type="text"
            onClick={() => setConfirmDelete(true)}
            className="text-destructive"
            icon={<Trash2 className="size-4" />}
          >
            Remove
          </CustomButton>
        ) : (
          <span />
        )}
        <CustomButton
          type="primary"
          onClick={submit}
          loading={upsert.isPending}
          disabled={upsert.isPending || !isValid}
        >
          Save webhook
        </CustomButton>
      </div>

      <WebhookTestPanel agentId={agentId} savedExists={savedExists} dirty={isDirty} />

      <CustomModal
        open={confirmDelete}
        onClose={() => (del.isPending ? undefined : setConfirmDelete(false))}
        title="Remove webhook?"
        description="Webhook-sourced profile variables will fall back to their default values on the next call."
        confirmText="Remove"
        confirmType="danger"
        confirmLoading={del.isPending}
        onConfirm={runDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}

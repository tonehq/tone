'use client';

import { Check, X } from 'lucide-react';
import { useState } from 'react';

import { CustomButton, TextInput } from '@/components/shared';
import { useTestAgentProfileWebhook } from '@/lib/api/agentProfileWebhook';
import type { WebhookTestResponse } from '@/types/agentProfileWebhook';
import { handleApiError } from '@/utils/helpers';

/** Test the SAVED webhook with a sample phone and show the raw response + which
 * configured source paths resolved. Disabled until a config is saved. */
export default function WebhookTestPanel({
  agentId,
  savedExists,
  dirty,
}: {
  agentId: string;
  savedExists: boolean;
  dirty: boolean;
}) {
  const [phone, setPhone] = useState('');
  const [result, setResult] = useState<WebhookTestResponse | null>(null);
  const test = useTestAgentProfileWebhook(agentId);

  const runTest = async () => {
    setResult(null);
    try {
      const res = await test.mutateAsync({ sample_phone: phone.trim() });
      setResult(res);
    } catch (err) {
      handleApiError(err);
    }
  };

  const disabled = !savedExists || !phone.trim() || test.isPending;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/30 p-3">
      <div>
        <p className="text-sm font-medium">Test webhook</p>
        <p className="text-xs text-muted-foreground">
          {savedExists
            ? 'Calls the saved webhook with a sample phone and shows which paths resolve.'
            : 'Save the webhook first, then test it with a sample phone number.'}
        </p>
      </div>
      {dirty && savedExists && (
        <p className="text-xs text-amber-600 dark:text-amber-500">
          You have unsaved changes — the test runs against the last saved config.
        </p>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <TextInput
            name="webhook-test-phone"
            label="Sample phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+15551234567"
            disabled={!savedExists}
          />
        </div>
        <CustomButton type="default" onClick={runTest} loading={test.isPending} disabled={disabled}>
          Test
        </CustomButton>
      </div>

      {result && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs">
            <span
              className={
                result.ok
                  ? 'rounded bg-emerald-500/10 px-2 py-0.5 font-medium text-emerald-600 dark:text-emerald-400'
                  : 'rounded bg-destructive/10 px-2 py-0.5 font-medium text-destructive'
              }
            >
              {result.status_code != null ? `HTTP ${result.status_code}` : 'Request failed'}
            </span>
            {result.error && <span className="text-destructive">{result.error}</span>}
          </div>

          {result.path_results.length > 0 && (
            <ul className="flex flex-col gap-1">
              {result.path_results.map((pr) => (
                <li key={pr.path} className="flex items-center gap-2 text-xs">
                  {pr.resolved ? (
                    <Check size={13} className="text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <X size={13} className="text-destructive" />
                  )}
                  <span className="font-mono">{pr.path}</span>
                  <span className="text-muted-foreground">
                    {pr.resolved ? `→ ${String(pr.value)}` : 'not found'}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {result.raw_response !== undefined && result.raw_response !== null && (
            <pre className="max-h-48 overflow-auto rounded-md bg-background p-2 font-mono text-[11px]">
              {typeof result.raw_response === 'string'
                ? result.raw_response
                : JSON.stringify(result.raw_response, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

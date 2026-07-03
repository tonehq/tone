'use client';

import { CustomButton, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import IntegrationConnectionPicker from '@/components/tools/IntegrationConnectionPicker';
import ParameterBuilder from '@/components/tools/ParameterBuilder';
import { AUTH_TYPE_OPTIONS, METHOD_COLORS, METHOD_OPTIONS } from '@/constants/toolForm';
import { type CustomToolFormData, customToolSchema } from '@/schemas/tool';
import type { ToolAuthType, ToolHttpMethod, ToolParametersSchema } from '@/types/tool';
import { cn } from '@/utils/cn';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useEffect, type ReactNode } from 'react';
import { useForm } from 'react-hook-form';

interface CustomToolFormProps {
  name: string;
  description: string;
  url: string;
  method: ToolHttpMethod;
  parameters: ToolParametersSchema;
  authType: ToolAuthType;
  authHeaderName: string;
  authApiKey: string;
  authBearerToken: string;
  authUsername: string;
  authPassword: string;
  /** Catalog row narrowing the connection picker. Consulted for the
   *  connection-capable auth types (``oauth`` / ``bearer`` / ``api_key``). */
  appIntegrationId: string | null;
  /** Stored connection backing this tool. Required credential source for
   *  ``oauth``; optional for ``bearer`` / ``api_key`` where it takes
   *  precedence over the inline secret. */
  oauthConnectionId: string | null;
  isActive: boolean;
  isEditMode: boolean;
  saving: boolean;
  onMethodChange: (value: ToolHttpMethod) => void;
  onParametersChange: (schema: ToolParametersSchema) => void;
  onAuthTypeChange: (value: ToolAuthType) => void;
  onAuthHeaderNameChange: (value: string) => void;
  onAuthApiKeyChange: (value: string) => void;
  onAuthBearerTokenChange: (value: string) => void;
  onAuthUsernameChange: (value: string) => void;
  onAuthPasswordChange: (value: string) => void;
  onAppIntegrationIdChange: (id: string | null) => void;
  onOAuthConnectionIdChange: (id: string | null) => void;
  onIsActiveChange: (value: boolean) => void;
  onSave: (data: CustomToolFormData) => void;
  onBack: () => void;
  /** Agents section (an ``AgentAttachmentPicker``) — owned by the page so the
   * form stays presentation-only. */
  agentsSection?: ReactNode;
}

export default function CustomToolForm({
  name,
  description,
  url,
  method,
  parameters,
  authType,
  authHeaderName,
  authApiKey,
  authBearerToken,
  authUsername,
  authPassword,
  appIntegrationId,
  oauthConnectionId,
  isActive,
  isEditMode,
  saving,
  onMethodChange,
  onParametersChange,
  onAuthTypeChange,
  onAuthHeaderNameChange,
  onAuthApiKeyChange,
  onAuthBearerTokenChange,
  onAuthUsernameChange,
  onAuthPasswordChange,
  onAppIntegrationIdChange,
  onOAuthConnectionIdChange,
  onIsActiveChange,
  onSave,
  onBack,
  agentsSection,
}: CustomToolFormProps) {
  const { control, handleSubmit, watch, reset } = useForm<CustomToolFormData>({
    resolver: zodResolver(customToolSchema),
    defaultValues: { name, description, url },
  });

  useEffect(() => {
    reset({ name, description, url });
  }, [name, description, url, reset]);

  const watchedName = watch('name');
  const paramCount = Object.keys(parameters?.properties ?? {}).length;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-background px-4 py-2">
        <div className="flex items-center gap-2">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <span className="text-[13px] font-medium text-foreground">
            {watchedName || (isEditMode ? 'Edit Tool' : 'New Tool')}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <CustomButton type="default" size="sm" onClick={onBack}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            size="sm"
            icon={saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save size={13} />}
            onClick={handleSubmit(onSave)}
            loading={saving}
          >
            {isEditMode ? 'Save' : 'Create'}
          </CustomButton>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
        <div className="mx-auto max-w-[680px] px-6 py-5">
          <div className="overflow-hidden rounded-xl border border-border bg-background shadow-sm">
            <div className="border-b border-border/60 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-[13px] font-semibold text-foreground">Tool Definition</h3>
                <CheckboxField
                  id="tool-is-active"
                  label="Active"
                  checked={isActive}
                  onCheckedChange={(checked) => onIsActiveChange(!!checked)}
                />
              </div>
              <div className="space-y-3">
                <TextInput
                  name="name"
                  control={control}
                  label="Function name"
                  placeholder="check_inventory"
                  isRequired
                  className="font-mono"
                />
                <TextAreaField
                  name="description"
                  control={control}
                  label="Description"
                  placeholder="Checks product inventory in real-time and returns availability, stock count, and pricing."
                  rows={2}
                  isRequired
                />
              </div>
            </div>

            <div className="border-b border-border/60 p-5">
              <h3 className="mb-3 text-[13px] font-semibold text-foreground">Request</h3>
              <div className="overflow-hidden rounded-lg border border-border">
                <div className="flex items-stretch">
                  <div className="flex shrink-0 items-center border-r border-border bg-muted/50 px-1">
                    <SelectInput
                      name="tool-method"
                      options={METHOD_OPTIONS}
                      value={method}
                      onValueChange={(v) => onMethodChange(v as ToolHttpMethod)}
                      triggerClassName="border-0 bg-transparent shadow-none focus:ring-0 font-mono text-[13px] font-semibold w-[88px]"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <TextInput
                      name="url"
                      control={control}
                      placeholder="https://api.example.com/inventory/{product_id}"
                      isRequired
                      className="rounded-none border-0 font-mono text-[13px] shadow-none focus-visible:ring-0"
                    />
                  </div>
                  <div className="flex shrink-0 items-center border-l border-border px-2.5">
                    <span
                      className={cn(
                        'inline-flex rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ring-1 ring-inset',
                        METHOD_COLORS[method] ?? 'bg-muted text-muted-foreground ring-border',
                      )}
                    >
                      {method}
                    </span>
                  </div>
                </div>
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                Use{' '}
                <code className="rounded bg-muted/80 px-1 py-px font-mono text-[10px] text-foreground">
                  {'{param}'}
                </code>{' '}
                placeholders for dynamic path segments, e.g.{' '}
                <code className="rounded bg-muted/80 px-1 py-px font-mono text-[10px] text-foreground">
                  /users/{'{user_id}'}
                </code>
              </p>
            </div>

            <div className="border-b border-border/60 p-5">
              <div className="mb-3 flex items-center gap-2">
                <h3 className="text-[13px] font-semibold text-foreground">Parameters</h3>
                {paramCount > 0 && (
                  <span className="inline-flex size-[18px] items-center justify-center rounded bg-primary/10 text-[10px] font-bold text-primary">
                    {paramCount}
                  </span>
                )}
              </div>
              <p className="mb-3 text-[11px] leading-relaxed text-muted-foreground">
                {method === 'GET'
                  ? 'Parameters will be sent as query string values.'
                  : 'Parameters will be sent as JSON request body. Any parameter matching a {placeholder} in the URL will be used as a path value instead.'}
              </p>
              <ParameterBuilder value={parameters} onChange={onParametersChange} />
            </div>

            <div className="p-5">
              <SelectInput
                name="tool-auth-type"
                label="Authentication"
                options={AUTH_TYPE_OPTIONS}
                value={authType}
                onValueChange={(v) => onAuthTypeChange(v as ToolAuthType)}
              />

              {/* Stored connections bridge tools onto saved credentials —
                  connected accounts (HubSpot, Slack, …) for OAuth, or custom
                  bearer / client-credentials entries from Integrations. The
                  runtime resolves a fresh token from the connection and injects
                  it as ``Authorization: Bearer <token>``; a linked connection
                  always wins over the inline secret below. */}
              {(authType === 'oauth' || authType === 'bearer' || authType === 'api_key') && (
                <div className="mt-3 rounded-lg bg-muted/40 p-3">
                  <IntegrationConnectionPicker
                    appIntegrationId={appIntegrationId}
                    oauthConnectionId={oauthConnectionId}
                    onAppIntegrationIdChange={onAppIntegrationIdChange}
                    onOAuthConnectionIdChange={onOAuthConnectionIdChange}
                  />
                  {authType !== 'oauth' && (
                    <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                      Optional — when a saved credential is linked it takes precedence over the
                      inline value below.
                    </p>
                  )}
                </div>
              )}

              {authType === 'api_key' && (
                <div className="mt-3 grid grid-cols-[140px_1fr] gap-3 rounded-lg bg-muted/40 p-3">
                  <TextInput
                    name="tool-auth-header"
                    label="Header"
                    placeholder="X-API-Key"
                    value={authHeaderName}
                    onChange={(e) => onAuthHeaderNameChange(e.target.value)}
                  />
                  <TextInput
                    name="tool-auth-api-key"
                    label="Value"
                    type="password"
                    placeholder="sk-..."
                    value={authApiKey}
                    onChange={(e) => onAuthApiKeyChange(e.target.value)}
                    className="font-mono text-[13px]"
                  />
                </div>
              )}

              {authType === 'bearer' && (
                <div className="mt-3 rounded-lg bg-muted/40 p-3">
                  <TextInput
                    name="tool-auth-bearer"
                    label="Token"
                    type="password"
                    placeholder="Enter bearer token"
                    value={authBearerToken}
                    onChange={(e) => onAuthBearerTokenChange(e.target.value)}
                    className="font-mono text-[13px]"
                  />
                </div>
              )}

              {authType === 'basic' && (
                <div className="mt-3 grid grid-cols-2 gap-3 rounded-lg bg-muted/40 p-3">
                  <TextInput
                    name="tool-auth-username"
                    label="Username"
                    placeholder="username"
                    value={authUsername}
                    onChange={(e) => onAuthUsernameChange(e.target.value)}
                  />
                  <TextInput
                    name="tool-auth-password"
                    label="Password"
                    type="password"
                    placeholder="password"
                    value={authPassword}
                    onChange={(e) => onAuthPasswordChange(e.target.value)}
                    className="font-mono text-[13px]"
                  />
                </div>
              )}
            </div>

            {agentsSection && (
              <div className="border-t border-border/60 p-5">
                <h3 className="mb-3 text-[13px] font-semibold text-foreground">Agents</h3>
                {agentsSection}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

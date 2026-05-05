'use client';

import { createToolAtom, updateToolAtom } from '@/atoms/ToolAtom';
import { CustomButton, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import ParameterBuilder from '@/components/tools/ParameterBuilder';
import { getTool } from '@/services/toolService';
import type {
  Tool,
  ToolAuthType,
  ToolCreatePayload,
  ToolHttpMethod,
  ToolParametersSchema,
} from '@/types/tool';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

interface ToolFormPageProps {
  toolId?: string;
}

const METHOD_OPTIONS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
  { value: 'PATCH', label: 'PATCH' },
];

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400',
  POST: 'bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-400',
  PUT: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400',
  DELETE: 'bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-500/10 dark:text-red-400',
  PATCH:
    'bg-violet-50 text-violet-700 ring-violet-600/20 dark:bg-violet-500/10 dark:text-violet-400',
};

const AUTH_TYPE_OPTIONS = [
  { value: 'none', label: 'No Authentication' },
  { value: 'api_key', label: 'API Key' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
];

export default function ToolFormPage({ toolId }: ToolFormPageProps) {
  const router = useRouter();
  const isEditMode = !!toolId;

  const [, createToolAction] = useAtom(createToolAtom);
  const [, updateToolAction] = useAtom(updateToolAtom);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState<ToolHttpMethod>('POST');
  const [parameters, setParameters] = useState<ToolParametersSchema>({});
  const [authType, setAuthType] = useState<ToolAuthType>('none');
  const [authHeaderName, setAuthHeaderName] = useState('');
  const [authApiKey, setAuthApiKey] = useState('');
  const [authBearerToken, setAuthBearerToken] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);

  const loadToolData = useCallback(async () => {
    if (!toolId) return;
    setLoading(true);
    try {
      const tool: Tool = await getTool(Number(toolId));
      setName(tool.name);
      setDescription(tool.description);
      setUrl(tool.url);
      setMethod((tool.method?.toUpperCase() as ToolHttpMethod) || 'POST');
      setParameters(tool.parameters ?? {});
      setAuthType(tool.auth_type ?? 'none');
      setIsActive(tool.is_active);
      const cfg = tool.auth_config ?? {};
      setAuthHeaderName(cfg.header_name ?? '');
      setAuthApiKey(cfg.api_key ?? '');
      setAuthBearerToken(cfg.token ?? '');
      setAuthUsername(cfg.username ?? '');
      setAuthPassword(cfg.password ?? '');
    } catch (error) {
      handleApiError(error);
      router.push('/tools');
    } finally {
      setLoading(false);
    }
  }, [toolId, router]);

  useEffect(() => {
    if (isEditMode) loadToolData();
  }, [isEditMode, loadToolData]);

  const buildAuthConfig = useCallback((): Record<string, string> | null => {
    switch (authType) {
      case 'api_key':
        return { header_name: authHeaderName || 'X-API-Key', api_key: authApiKey };
      case 'bearer':
        return { token: authBearerToken };
      case 'basic':
        return { username: authUsername, password: authPassword };
      default:
        return null;
    }
  }, [authType, authHeaderName, authApiKey, authBearerToken, authUsername, authPassword]);

  const handleSave = async () => {
    if (!name.trim() || !description.trim() || !url.trim()) return;
    const payload: ToolCreatePayload = {
      name: name.trim(),
      description: description.trim(),
      url: url.trim(),
      method,
      parameters,
      auth_type: authType,
      auth_config: buildAuthConfig(),
      is_active: isActive,
    };
    setSaving(true);
    try {
      if (isEditMode) {
        await updateToolAction({ toolId: Number(toolId), payload });
        showToast.success('Tool updated successfully');
      } else {
        await createToolAction(payload);
        showToast.success('Tool created successfully');
        router.push('/tools');
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setSaving(false);
    }
  };

  const handleParametersChange = useCallback((schema: ToolParametersSchema) => {
    setParameters(schema);
  }, []);

  const isValid = name.trim().length > 0 && description.trim().length > 0 && url.trim().length > 0;

  if (loading) {
    return (
      <div className="flex h-full flex-col p-6">
        <div className="flex items-center gap-3">
          <div className="size-8 animate-pulse rounded-lg bg-muted" />
          <div className="h-4 w-28 animate-pulse rounded bg-muted" />
        </div>
        <div className="mx-auto mt-8 w-full max-w-[680px] space-y-3">
          {[80, 60, 100, 48].map((h, i) => (
            <div key={i} className="animate-pulse rounded-lg bg-muted" style={{ height: h }} />
          ))}
        </div>
      </div>
    );
  }

  const paramCount = Object.keys(parameters?.properties ?? {}).length;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-background px-4 py-2">
        <div className="flex items-center gap-2">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={() => router.push('/tools')}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <span className="text-[13px] font-medium text-foreground">
            {name || (isEditMode ? 'Edit Tool' : 'New Tool')}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <CustomButton type="default" size="sm" onClick={() => router.push('/tools')}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            size="sm"
            icon={saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save size={13} />}
            onClick={handleSave}
            loading={saving}
            disabled={!isValid}
          >
            {isEditMode ? 'Save' : 'Create'}
          </CustomButton>
        </div>
      </div>

      {/* ── Form ────────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
        <div className="mx-auto max-w-[680px] px-6 py-5">
          <div className="overflow-hidden rounded-xl border border-border bg-background shadow-sm">
            {/* ── Section: Definition ──────────────────────────── */}
            <div className="border-b border-border/60 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-[13px] font-semibold text-foreground">Tool Definition</h3>
                <CheckboxField
                  id="tool-is-active"
                  label="Active"
                  checked={isActive}
                  onCheckedChange={(checked) => setIsActive(!!checked)}
                />
              </div>
              <div className="space-y-3">
                <TextInput
                  name="tool-name"
                  label="Function name"
                  placeholder="check_inventory"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  isRequired
                  className="font-mono"
                />
                <TextAreaField
                  name="tool-description"
                  label="Description"
                  placeholder="Checks product inventory in real-time and returns availability, stock count, and pricing."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  isRequired
                />
              </div>
            </div>

            {/* ── Section: Request ─────────────────────────────── */}
            <div className="border-b border-border/60 p-5">
              <h3 className="mb-3 text-[13px] font-semibold text-foreground">Request</h3>
              <div className="overflow-hidden rounded-lg border border-border">
                <div className="flex items-stretch">
                  <div className="flex shrink-0 items-center border-r border-border bg-muted/50 px-1">
                    <SelectInput
                      name="tool-method"
                      options={METHOD_OPTIONS}
                      value={method}
                      onValueChange={(v) => setMethod(v as ToolHttpMethod)}
                      triggerClassName="border-0 bg-transparent shadow-none focus:ring-0 font-mono text-[13px] font-semibold w-[88px]"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <TextInput
                      name="tool-url"
                      placeholder="https://api.example.com/inventory/{product_id}"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
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

            {/* ── Section: Parameters ──────────────────────────── */}
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
              <ParameterBuilder value={parameters} onChange={handleParametersChange} />
            </div>

            {/* ── Section: Authentication ──────────────────────── */}
            <div className="p-5">
              <h3 className="mb-3 text-[13px] font-semibold text-foreground">Authentication</h3>
              <SelectInput
                name="tool-auth-type"
                options={AUTH_TYPE_OPTIONS}
                value={authType}
                onValueChange={(v) => setAuthType(v as ToolAuthType)}
              />

              {authType === 'api_key' && (
                <div className="mt-3 grid grid-cols-[140px_1fr] gap-3 rounded-lg bg-muted/40 p-3">
                  <TextInput
                    name="tool-auth-header"
                    label="Header"
                    placeholder="X-API-Key"
                    value={authHeaderName}
                    onChange={(e) => setAuthHeaderName(e.target.value)}
                  />
                  <TextInput
                    name="tool-auth-api-key"
                    label="Value"
                    type="password"
                    placeholder="sk-..."
                    value={authApiKey}
                    onChange={(e) => setAuthApiKey(e.target.value)}
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
                    onChange={(e) => setAuthBearerToken(e.target.value)}
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
                    onChange={(e) => setAuthUsername(e.target.value)}
                  />
                  <TextInput
                    name="tool-auth-password"
                    label="Password"
                    type="password"
                    placeholder="password"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    className="font-mono text-[13px]"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

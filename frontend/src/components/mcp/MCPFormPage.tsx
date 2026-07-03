/* eslint-disable @typescript-eslint/no-use-before-define */
'use client';

import { fetchMcpServersAtom, upsertMcpServerAtom } from '@/atoms/MCPAtom';
import HttpHeadersBuilder from '@/components/mcp/HttpHeadersBuilder';
import { finalizeAttachmentAndRedirect } from '@/services/agentAttachmentService';
import { readAttachContext } from '@/utils/agentAttachmentContext';
import {
  AppLoader,
  CustomButton,
  CustomModal,
  ScopeStatus,
  SelectInput,
  SliderField,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import AgentAttachmentPicker from '@/components/tools/AgentAttachmentPicker';
import SettingsSection from '@/components/tools/SettingsSection';
import { Switch } from '@/components/ui/switch';
import { useGoBack } from '@/hooks/useGoBack';
import { NO_APP_INTEGRATION, useIntegrationConnections } from '@/hooks/useIntegrationConnections';
import { getAgentsByMcpServer, getMcpServer } from '@/services/mcpServerService';
import { discoverMcpOAuth } from '@/services/oauthService';
import type { MCPAuthType, MCPServer, MCPServerUpsertPayload } from '@/types/mcp';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import {
  ArrowLeft,
  Bot,
  Boxes,
  Cable,
  Check,
  Clock,
  Globe,
  KeyRound,
  Loader2,
  Power,
  Save,
  Settings,
  Signal,
  Sparkles,
} from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Controller, useFieldArray, useForm } from 'react-hook-form';

type TransportType = 'shttp' | 'sse';

// Radix <Select.Item> forbids an empty-string value (it's reserved for clearing the selection),
// so the "no connection" choice uses a sentinel that we translate back to null on save.
const NO_OAUTH_CONNECTION = '__none__';

// Auto-discover OAuth navigates away to the provider and back, which would otherwise discard the
// in-progress form. We stash the form in sessionStorage under this key and restore it on return.
const MCP_FORM_DRAFT_KEY = 'mcp-form-oauth-draft';

interface HttpHeaderField {
  key: string;
  value: string;
}

interface MCPFormState {
  name: string;
  description: string;
  server_url: string;
  timeout: number;
  transport_type: TransportType;
  use_bearer_token: boolean;
  bearer_token: string;
  use_api_key: boolean;
  api_key: string;
  oauth_connection_id: string;
  /** Linked catalog entry. Drives the OAuth connection picker filter. */
  app_integration_id: string;
  http_headers: HttpHeaderField[];
  is_active: boolean;
}

const DEFAULT_VALUES: MCPFormState = {
  name: '',
  description: '',
  server_url: '',
  timeout: 20,
  transport_type: 'shttp',
  use_bearer_token: false,
  bearer_token: '',
  use_api_key: false,
  api_key: '',
  oauth_connection_id: NO_OAUTH_CONNECTION,
  app_integration_id: NO_APP_INTEGRATION,
  http_headers: [],
  is_active: true,
};

function getHostname(url: string): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

function getApexDomain(hostname: string): string {
  const parts = hostname.split('.');
  if (parts.length <= 2) return hostname;
  const lastTwo = parts.slice(-2).join('.');
  const dualTier = new Set(['co.uk', 'com.au', 'co.in', 'co.jp', 'com.br', 'co.nz', 'com.mx']);
  if (dualTier.has(lastTwo)) return parts.slice(-3).join('.');
  return lastTwo;
}

function getFaviconUrl(hostname: string | null): string | null {
  if (!hostname) return null;
  return `https://www.google.com/s2/favicons?domain=${getApexDomain(hostname)}&sz=64`;
}

/** Derive the ``auth_type`` string the backend expects from the form state.
 *
 * The static-credential toggles (bearer / api_key) name the auth type when
 * active — a selected connection can coexist with them (it's sent separately
 * as ``oauth_connection_id`` and takes precedence at runtime). ``oauth`` is
 * only derived when a connection is the sole credential source; everything
 * else is ``none``. Kept as a pure function so the payload builder and any
 * "what auth is active?" label reads from a single source.
 */
function deriveAuthType(s: MCPFormState): MCPAuthType {
  if (s.use_bearer_token && s.bearer_token.trim()) return 'bearer';
  if (s.use_api_key && s.api_key.trim()) return 'api_key';
  if (s.oauth_connection_id && s.oauth_connection_id !== NO_OAUTH_CONNECTION) return 'oauth';
  return 'none';
}

function serverToFormState(s: MCPServer): MCPFormState {
  const auth = s.auth_config ?? {};
  const meta = (s.meta_data ?? {}) as { timeout?: number; http_headers?: Record<string, string> };
  const headersMap = meta.http_headers ?? {};
  // Prefer the explicit ``auth_type`` (post-migration rows). Legacy rows without
  // it fall back to inferring the two toggles from ``auth_config`` keys — same
  // behavior the form had before this column existed.
  const useBearer = s.auth_type != null ? s.auth_type === 'bearer' : !!auth.bearer_token;
  const useApiKey = s.auth_type != null ? s.auth_type === 'api_key' : !!auth.api_key;
  return {
    name: s.name ?? '',
    description: s.description ?? '',
    server_url: s.server_url ?? '',
    timeout: typeof meta.timeout === 'number' ? meta.timeout : 20,
    transport_type: s.transport_type === 'streamable_http' ? 'shttp' : 'sse',
    use_bearer_token: useBearer,
    bearer_token: auth.bearer_token ?? '',
    use_api_key: useApiKey,
    api_key: auth.api_key ?? '',
    oauth_connection_id: s.oauth_connection_id ?? NO_OAUTH_CONNECTION,
    app_integration_id: s.app_integration_id ?? NO_APP_INTEGRATION,
    http_headers: Object.entries(headersMap).map(([key, value]) => ({
      key,
      value: String(value),
    })),
    is_active: !!s.is_active,
  };
}

function formStateToUpsertPayload(s: MCPFormState, id?: string): MCPServerUpsertPayload {
  const authConfig: Record<string, string> = {};
  if (s.use_bearer_token && s.bearer_token.trim()) authConfig.bearer_token = s.bearer_token;
  if (s.use_api_key && s.api_key.trim()) authConfig.api_key = s.api_key;

  const headersMap = Object.fromEntries(
    s.http_headers.filter((h) => h.key.trim()).map((h) => [h.key.trim(), h.value]),
  );

  return {
    ...(id ? { id } : {}),
    name: s.name,
    description: s.description,
    server_url: s.server_url,
    transport_type: s.transport_type === 'shttp' ? 'streamable_http' : 'sse',
    auth_type: deriveAuthType(s),
    auth_config: Object.keys(authConfig).length > 0 ? authConfig : null,
    oauth_connection_id:
      s.oauth_connection_id && s.oauth_connection_id !== NO_OAUTH_CONNECTION
        ? s.oauth_connection_id
        : null,
    app_integration_id:
      s.app_integration_id && s.app_integration_id !== NO_APP_INTEGRATION
        ? s.app_integration_id
        : null,
    meta_data: { timeout: s.timeout, http_headers: headersMap },
    is_active: s.is_active,
  };
}

interface MCPFormPageProps {
  serverId?: string;
}

export default function MCPFormPage({ serverId }: MCPFormPageProps = {}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isEditMode = typeof serverId === 'string' && serverId.length > 0;

  // Present only when opened via the agent config "New MCP server" button —
  // see ``ToolsMcpStep`` and ``utils/agentAttachmentContext``.
  const attachCtx = useMemo(() => readAttachContext(searchParams), [searchParams]);

  const [, upsertServer] = useAtom(upsertMcpServerAtom);
  const [, fetchServers] = useAtom(fetchMcpServersAtom);
  const [loadingServer, setLoadingServer] = useState<boolean>(isEditMode);
  const [saving, setSaving] = useState(false);
  const [discovering, setDiscovering] = useState(false);

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    settings: true,
    server: true,
    protocol: true,
    agents: true,
    status: true,
  });

  // Agents section — attachments sync to each agent's PUBLISHED version.
  // ``agentsTouched`` gates the payload: agent_ids is only sent when the user
  // actually changed the list, so an untouched save never rewrites attachments.
  const [attachedAgentIds, setAttachedAgentIds] = useState<string[]>([]);
  const [agentsTouched, setAgentsTouched] = useState(false);
  const [agentsLoading, setAgentsLoading] = useState(isEditMode);
  const [agentsLoadFailed, setAgentsLoadFailed] = useState(false);
  // Server-side baseline of attached agents — the detach confirmation compares
  // against this, and it's refreshed after every successful save.
  const initialAgentIdsRef = useRef<string[]>([]);
  // A save that would detach agents parks its payload here until the user
  // confirms via the modal below.
  const [pendingDetachSave, setPendingDetachSave] = useState<{
    payload: MCPServerUpsertPayload;
    count: number;
  } | null>(null);

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const { control, handleSubmit, watch, reset, setValue, getValues } = useForm<MCPFormState>({
    defaultValues: DEFAULT_VALUES,
  });

  const { fields, append, remove } = useFieldArray<MCPFormState, 'http_headers', 'id'>({
    control,
    name: 'http_headers',
  });

  // Catalog + integrations + OAuth connections are owned by a shared hook so
  // this form and ``BuiltInToolForm`` stay in lockstep on fetch / filter / race
  // semantics. The hook fetches catalog + integrations in parallel on mount
  // and refetches connections server-side filtered whenever the picker below
  // changes — no client-side filtering, no N+1.
  useEffect(() => {
    // Returning from an Auto-discover OAuth round-trip: restore the stashed form and pre-select the
    // freshly created connection instead of reloading the saved server (which would lose the edits
    // the user had in flight). See onDiscoverOAuth.
    const params = new URLSearchParams(window.location.search);
    if (params.get('mcp_oauth') === 'success') {
      const newConnectionId = params.get('connection_id');
      const draft = sessionStorage.getItem(MCP_FORM_DRAFT_KEY);
      sessionStorage.removeItem(MCP_FORM_DRAFT_KEY);
      if (draft) {
        try {
          const { __agent_ids, __agents_touched, __agent_baseline, ...parsed } = JSON.parse(
            draft,
          ) as MCPFormState & {
            __agent_ids?: string[];
            __agents_touched?: boolean;
            __agent_baseline?: string[];
          };
          if (newConnectionId) parsed.oauth_connection_id = newConnectionId;
          // Agent selection (and its server baseline, used by the detach
          // confirmation) rides along in the stash so the OAuth round-trip
          // doesn't silently drop it.
          if (Array.isArray(__agent_ids)) {
            setAttachedAgentIds(__agent_ids);
            setAgentsTouched(!!__agents_touched);
          }
          if (Array.isArray(__agent_baseline)) {
            initialAgentIdsRef.current = __agent_baseline;
          }
          reset(parsed);
        } catch {
          if (newConnectionId) setValue('oauth_connection_id', newConnectionId);
        }
      } else if (newConnectionId) {
        setValue('oauth_connection_id', newConnectionId);
      }
      setLoadingServer(false);
      setAgentsLoading(false);
      // Strip the one-shot query params so a refresh doesn't re-trigger the restore.
      window.history.replaceState(null, '', window.location.pathname);
      return;
    }

    if (!isEditMode || !serverId) return;
    let cancelled = false;
    setLoadingServer(true);
    getMcpServer(serverId)
      .then((server) => {
        if (!cancelled) reset(serverToFormState(server));
      })
      .catch((error) => {
        if (!cancelled) handleApiError(error);
      })
      .finally(() => {
        if (!cancelled) setLoadingServer(false);
      });
    // Attachments load separately: a failure here disables the Agents section
    // (so a save can't blindly detach) without killing the form.
    getAgentsByMcpServer(serverId)
      .then((refs) => {
        if (cancelled) return;
        const ids = refs.map((r) => r.id);
        setAttachedAgentIds(ids);
        initialAgentIdsRef.current = ids;
        setAgentsLoadFailed(false);
      })
      .catch(() => {
        if (!cancelled) setAgentsLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) setAgentsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isEditMode, serverId, reset, setValue]);

  const watchedHeaders = watch('http_headers');
  const watchedName = watch('name');
  const watchedDescription = watch('description') ?? '';
  const watchedIsActive = watch('is_active');
  const watchedProtocol = watch('transport_type');
  const watchedTimeout = watch('timeout');
  const watchedServerUrl = watch('server_url') ?? '';
  const watchedOAuthId = watch('oauth_connection_id') ?? '';
  const watchedAppIntegrationId = watch('app_integration_id') ?? NO_APP_INTEGRATION;
  const { appIntegrations, oauthConnections, catalog } =
    useIntegrationConnections(watchedAppIntegrationId);
  const watchedUseBearer = watch('use_bearer_token');
  const watchedUseApiKey = watch('use_api_key');

  const hostname = getHostname(watchedServerUrl);
  const protocolLabel = watchedProtocol === 'shttp' ? 'SHTTP' : 'SSE';

  // Single source of truth for "which auth is active", shown both in the rail and chips.
  const authLabel =
    watchedOAuthId && watchedOAuthId !== NO_OAUTH_CONNECTION
      ? 'OAuth'
      : watchedUseBearer
        ? 'Bearer'
        : watchedUseApiKey
          ? 'API key'
          : 'None';

  const selectedConnection = oauthConnections.find((c) => c.id === watchedOAuthId) ?? null;
  // Picker for the catalog-entry filter. ``__none__`` sentinel keeps Radix happy.
  const appIntegrationOptions = [
    { value: NO_APP_INTEGRATION, label: 'None — show all connections' },
    ...appIntegrations.map((i) => ({
      value: i.id,
      label: i.display_name,
    })),
  ];
  const connectionOptions = [
    { value: NO_OAUTH_CONNECTION, label: 'None — use static headers' },
    // Skip in-flight MCP discovery handshakes (status 'pending') — they hold no usable token yet,
    // so picking one would fail validation at save. Mirrors the filter in oauth-connection-grid.
    ...oauthConnections
      .filter((c) => c.public_metadata?.status !== 'pending')
      .map((c) => ({
        value: c.id,
        label: `${c.public_metadata?.user_email || c.label || c.provider_slug} (${c.provider_slug})`,
      })),
  ];
  const requiredScopesForConnection = selectedConnection
    ? (catalog.find((p) => p.slug === selectedConnection.provider_slug)?.scopes ?? [])
    : [];

  const onSave = async (data: MCPFormState) => {
    const payload: MCPServerUpsertPayload = {
      ...formStateToUpsertPayload(data, isEditMode ? serverId : undefined),
      ...(agentsTouched && !agentsLoadFailed ? { agent_ids: attachedAgentIds } : {}),
    };
    // Detaching is destructive for live agents — a save that would remove the
    // server from previously-attached agents must be confirmed first.
    if (payload.agent_ids) {
      const selected = new Set(payload.agent_ids);
      const removedCount = initialAgentIdsRef.current.filter((id) => !selected.has(id)).length;
      if (removedCount > 0) {
        setPendingDetachSave({ payload, count: removedCount });
        return;
      }
    }
    await doSave(payload);
  };

  const doSave = async (payload: MCPServerUpsertPayload) => {
    setSaving(true);
    try {
      const savedServer = await upsertServer(payload);
      await fetchServers();
      const summary = savedServer?.attachment_summary;
      showToast.success(
        isEditMode ? 'MCP server updated successfully' : 'MCP server created successfully',
        summary && (summary.attached > 0 || summary.detached > 0)
          ? `Attached to ${summary.attached} agent(s), detached from ${summary.detached}.`
          : undefined,
      );
      if (savedServer?.attachment_warnings?.length) {
        showToast.warning(
          'Some agent attachments were skipped',
          savedServer.attachment_warnings.join(' • '),
          8,
        );
      }
      if (payload.agent_ids) initialAgentIdsRef.current = payload.agent_ids;
      setAgentsTouched(false);
      if (isEditMode) return;
      // When launched from the agent config page, attach the new MCP server
      // to that agent's viewing version and bounce back — same flow as tools.
      await finalizeAttachmentAndRedirect({
        router,
        attachCtx,
        kind: 'mcp_server',
        itemId: savedServer?.id,
        attachedMessage: 'MCP server attached to the agent version',
        fallbackRedirect: '/mcp',
      });
    } catch (error) {
      handleApiError(error);
    } finally {
      setSaving(false);
    }
  };

  const onDiscoverOAuth = async () => {
    if (!watchedServerUrl.trim()) {
      showToast.error('Enter the server URL first');
      return;
    }
    setDiscovering(true);
    try {
      // Stash the in-progress form (plus the Agents selection, which lives
      // outside RHF) and tell the backend where to send the user back to, so
      // the OAuth round-trip returns with edits intact and the new connection
      // selected.
      sessionStorage.setItem(
        MCP_FORM_DRAFT_KEY,
        JSON.stringify({
          ...getValues(),
          __agent_ids: attachedAgentIds,
          __agents_touched: agentsTouched,
          __agent_baseline: initialAgentIdsRef.current,
        }),
      );
      const url = await discoverMcpOAuth(
        watchedServerUrl.trim(),
        watchedName || undefined,
        window.location.pathname,
        watchedAppIntegrationId && watchedAppIntegrationId !== NO_APP_INTEGRATION
          ? watchedAppIntegrationId
          : undefined,
      );
      window.location.href = url;
    } catch (error) {
      sessionStorage.removeItem(MCP_FORM_DRAFT_KEY);
      handleApiError(error);
      setDiscovering(false);
    }
  };

  const onBack = useGoBack('/mcp');

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <CustomModal
        open={!!pendingDetachSave}
        onClose={() => setPendingDetachSave(null)}
        title="Detach from agents?"
        description={
          pendingDetachSave
            ? `Saving will detach this MCP server from ${pendingDetachSave.count} agent${
                pendingDetachSave.count === 1 ? '' : 's'
              } currently using it on their live version. Calls on ${
                pendingDetachSave.count === 1 ? 'that agent' : 'those agents'
              } will no longer reach this server's tools.`
            : undefined
        }
        confirmText="Detach and save"
        confirmType="danger"
        confirmLoading={saving}
        onConfirm={() => {
          if (!pendingDetachSave) return;
          const { payload } = pendingDetachSave;
          setPendingDetachSave(null);
          doSave(payload);
        }}
      />

      {/* Top bar */}
      <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-border bg-background py-3">
        <div className="flex min-w-0 items-center gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={onBack}
            aria-label="Back to MCP servers"
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <PreviewFavicon key={hostname ?? 'top'} hostname={hostname} size="sm" />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
                {watchedName || (isEditMode ? 'Edit MCP Server' : 'New MCP Server')}
              </h1>
              <StatusPill active={!!watchedIsActive} />
            </div>
            <p className="truncate text-[11.5px] text-muted-foreground">
              {hostname ?? 'Configure endpoint, auth, and protocol'}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <CustomButton type="default" size="sm" onClick={onBack} disabled={saving}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            size="sm"
            icon={saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            onClick={handleSubmit(onSave)}
            loading={saving}
          >
            {isEditMode ? 'Save Changes' : 'Save'}
          </CustomButton>
        </div>

        {/* Hairline gradient accent under the top bar */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -bottom-px h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
        />
      </div>

      {/* Two-column layout: left rail + form */}
      <div className="min-h-0 flex-1 overflow-hidden bg-muted/30">
        <div className="grid h-full grid-cols-1 lg:grid-cols-[260px_1fr]">
          {/* LEFT RAIL — preview + section nav */}
          <aside className="hidden border-r border-border bg-background lg:flex lg:flex-col">
            <div className="sticky top-0 flex flex-col gap-5 px-6 py-7">
              {/* Preview */}
              <div>
                <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  Preview
                </span>

                <div className="mt-3 flex items-start gap-2.5">
                  <PreviewFavicon key={hostname ?? 'none'} hostname={hostname} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-semibold text-foreground">
                      {watchedName || (
                        <span className="text-muted-foreground/70">Unnamed server</span>
                      )}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-[11.5px] leading-relaxed text-muted-foreground">
                      {watchedDescription || 'Description will appear here.'}
                    </p>
                  </div>
                </div>

                <dl className="mt-3 space-y-1.5 border-t border-border/60 pt-3 text-[11.5px]">
                  <RailRow label="Protocol">
                    <span className="font-mono uppercase tracking-wide">{protocolLabel}</span>
                  </RailRow>
                  <RailRow label="Host">
                    {hostname ? (
                      <span className="block max-w-[140px] truncate font-mono">{hostname}</span>
                    ) : (
                      <span className="text-muted-foreground/70">—</span>
                    )}
                  </RailRow>
                  <RailRow label="Timeout">
                    <span className="font-mono tabular-nums">{watchedTimeout}s</span>
                  </RailRow>
                  <RailRow label="Auth">
                    <span
                      className={cn(
                        'font-mono',
                        authLabel === 'None' ? 'text-muted-foreground/70' : 'text-foreground',
                      )}
                    >
                      {authLabel}
                    </span>
                  </RailRow>
                  <RailRow label="Headers">
                    <span className="font-mono tabular-nums">{fields.length}</span>
                  </RailRow>
                </dl>
              </div>
            </div>
          </aside>

          {/* RIGHT COLUMN — scrollable form */}
          <div className="relative min-h-0 overflow-auto">
            {loadingServer && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/70 backdrop-blur-sm">
                <AppLoader label="Loading server..." className="min-h-0" />
              </div>
            )}
            <div className="mx-auto max-w-[780px] space-y-4 px-6 py-8 lg:px-8">
              {/* Header band */}
              <div
                className={cn(
                  'relative overflow-hidden rounded-xl border border-border p-5 sm:p-6',
                  'bg-gradient-to-br from-primary/5 via-background to-background',
                  'dark:from-primary/10 dark:via-background dark:to-muted/20',
                )}
              >
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute -right-16 -top-16 size-48 rounded-full bg-primary/10 blur-3xl dark:bg-primary/15"
                />

                <div className="relative">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Boxes size={15} />
                    </span>
                    <h2 className="text-[15px] font-semibold tracking-tight text-foreground">
                      Configure MCP Server
                    </h2>
                  </div>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
                    Set up the endpoint, authentication, and protocol your agents will use to reach
                    this Model Context Protocol server.
                  </p>

                  <div className="mt-4 flex flex-wrap items-center gap-1.5">
                    <Chip icon={<Signal size={11} />} label={protocolLabel} />
                    <Chip icon={<Clock size={11} />} label={`${watchedTimeout}s timeout`} />
                    <Chip icon={<Sparkles size={11} />} label={`${authLabel} auth`} />
                    <Chip
                      icon={<KeyRound size={11} />}
                      label={`${fields.length} ${fields.length === 1 ? 'header' : 'headers'}`}
                    />
                  </div>
                </div>
              </div>

              {/* Tool Settings */}
              <SettingsSection
                title="Tool Settings"
                description="Configure the basic settings for this server"
                icon={Settings}
                iconColor="text-foreground/70"
                iconBg="bg-foreground/5 dark:bg-foreground/10"
                isOpen={openSections.settings}
                onToggle={() => toggleSection('settings')}
              >
                <div className="space-y-5">
                  {/* Linked integration is asked FIRST — it scopes the rest of the form
                      (server URL hints, OAuth account dropdown filter, new-connection tagging).
                      Defaults to "None" so existing forms continue to work unchanged. */}
                  <SelectInput
                    name="app_integration_id"
                    control={control}
                    label="Linked integration"
                    placeholder="None — show all connections"
                    options={appIntegrationOptions}
                    helperText="Filters the OAuth account list below to this integration only."
                  />
                  <TextInput
                    name="name"
                    control={control}
                    rules={{ required: 'Server name is required' }}
                    label="Server Name"
                    placeholder="clickup_mcp"
                    isRequired
                    className="font-mono"
                  />
                  <div className="relative">
                    <TextAreaField
                      name="description"
                      control={control}
                      label="Description"
                      placeholder="Describe what this server provides to your agents"
                      rows={4}
                      maxLength={1000}
                    />
                    <span className="absolute right-0 top-0 text-[11px] tabular-nums text-muted-foreground">
                      {watchedDescription.length}/1000
                    </span>
                  </div>
                </div>
              </SettingsSection>

              {/* Server Settings */}
              <SettingsSection
                title="Server Settings"
                description="Endpoint, timeout, authentication, and headers"
                icon={Globe}
                iconColor="text-sky-600 dark:text-sky-400"
                iconBg="bg-sky-50 dark:bg-sky-500/10"
                isOpen={openSections.server}
                onToggle={() => toggleSection('server')}
              >
                <div className="space-y-6">
                  <TextAreaField
                    name="server_url"
                    control={control}
                    rules={{ required: 'Server URL is required' }}
                    label="Server URL"
                    helperText="Webhook and tool request endpoint."
                    placeholder="https://api.example.com/mcp"
                    rows={2}
                    isRequired
                  />

                  <Controller
                    name="timeout"
                    control={control}
                    render={({ field }) => (
                      <div
                        className={cn(
                          'rounded-lg border border-border p-4',
                          'bg-gradient-to-br from-muted/20 to-muted/40',
                          'dark:from-muted/10 dark:to-muted/30',
                        )}
                      >
                        <div className="grid items-center gap-5 sm:grid-cols-[140px_1fr]">
                          <TimeoutDial value={Number(field.value ?? 20)} />
                          <div>
                            <p className="text-[13px] font-semibold text-foreground">
                              Request Timeout
                            </p>
                            <p className="mt-0.5 text-[12px] text-muted-foreground">
                              Maximum time to wait for an MCP response before aborting.
                            </p>
                            <div className="mt-4">
                              <SliderField
                                name="timeout"
                                value={Number(field.value ?? 20)}
                                onValueChange={(v) => field.onChange(v)}
                                min={1}
                                max={300}
                                step={1}
                                showLabels={false}
                              />
                              <div className="mt-1 flex justify-between text-[11px] tabular-nums text-muted-foreground">
                                <span>1 sec</span>
                                <span>300 sec</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  />

                  <div className="space-y-3 rounded-lg border border-border bg-background p-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <KeyRound size={14} className="text-muted-foreground" />
                        <p className="text-[13px] font-semibold text-foreground">Authentication</p>
                      </div>
                      <p className="mt-0.5 text-[12px] text-muted-foreground">
                        Optional — enable each method only if your MCP server requires it.
                      </p>
                    </div>

                    {/* OAuth connection — preferred for providers like ClickUp, Google, Slack.
                        Resolves a fresh bearer token at call time and validates scopes. */}
                    <div className="rounded-md border border-border/60 bg-muted/20 p-3">
                      <div className="flex items-center gap-2">
                        <Sparkles size={13} className="text-violet-500" />
                        <p className="text-[12.5px] font-semibold text-foreground">
                          Use an OAuth connection
                        </p>
                      </div>
                      <p className="mt-0.5 text-[11.5px] text-muted-foreground">
                        Authenticate with a connected account instead of a static token. Takes
                        precedence over the static credentials below. Manage connections in
                        Integrations.
                      </p>
                      <div className="mt-3 border-t border-border/60 pt-3">
                        <SelectInput
                          name="oauth_connection_id"
                          control={control}
                          label="OAuth connection"
                          placeholder="Select a connection"
                          options={connectionOptions}
                        />
                        {selectedConnection && (
                          <div className="mt-2.5">
                            <ScopeStatus
                              granted={selectedConnection.public_metadata?.scopes}
                              required={requiredScopesForConnection}
                            />
                          </div>
                        )}

                        {/* Auto-discover OAuth for any spec-compliant MCP server (DCR + PKCE). */}
                        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border/60 pt-3">
                          <p className="text-[11.5px] text-muted-foreground">
                            No connection yet? Auto-discover this server&apos;s OAuth and authorize.
                          </p>
                          <CustomButton
                            type="default"
                            size="sm"
                            onClick={onDiscoverOAuth}
                            loading={discovering}
                            disabled={!watchedServerUrl.trim()}
                            className="shrink-0 gap-1.5"
                          >
                            <Sparkles size={13} />
                            Auto-discover
                          </CustomButton>
                        </div>
                      </div>
                    </div>

                    <Controller
                      name="use_bearer_token"
                      control={control}
                      render={({ field }) => (
                        <div className="rounded-md border border-border/60 bg-muted/20 p-3">
                          <CheckboxField
                            id="mcp-use-bearer-token"
                            label="Use Bearer Token"
                            checked={!!field.value}
                            onCheckedChange={(checked) => field.onChange(!!checked)}
                          />
                          {field.value && (
                            <div className="mt-3 border-t border-border/60 pt-3">
                              <TextInput
                                name="bearer_token"
                                control={control}
                                type="password"
                                label="Bearer Token"
                                placeholder="Enter bearer token"
                                helperText="Stored under auth_config.bearer_token."
                                className="font-mono text-[13px]"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    />

                    <Controller
                      name="use_api_key"
                      control={control}
                      render={({ field }) => (
                        <div className="rounded-md border border-border/60 bg-muted/20 p-3">
                          <CheckboxField
                            id="mcp-use-api-key"
                            label="Use API Key"
                            checked={!!field.value}
                            onCheckedChange={(checked) => field.onChange(!!checked)}
                          />
                          {field.value && (
                            <div className="mt-3 border-t border-border/60 pt-3">
                              <TextInput
                                name="api_key"
                                control={control}
                                type="password"
                                label="API Key"
                                placeholder="sk-..."
                                helperText="Stored under auth_config.api_key."
                                className="font-mono text-[13px]"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    />
                  </div>

                  <div>
                    <div className="mb-2 flex items-end justify-between">
                      <div>
                        <p className="text-[13px] font-semibold text-foreground">HTTP Headers</p>
                        <p className="mt-0.5 text-[12px] text-muted-foreground">
                          Optional headers sent with every MCP request.
                        </p>
                      </div>
                      {fields.length > 0 && (
                        <span className="text-[11px] tabular-nums text-muted-foreground">
                          {fields.length} {fields.length === 1 ? 'header' : 'headers'}
                        </span>
                      )}
                    </div>
                    <HttpHeadersBuilder
                      rows={fields.map((f, i) => ({
                        id: f.id,
                        key: watchedHeaders[i]?.key ?? '',
                        value: watchedHeaders[i]?.value ?? '',
                      }))}
                      onAdd={() => append({ key: '', value: '' })}
                      onRemove={(id) => {
                        const idx = fields.findIndex((f) => f.id === id);
                        if (idx >= 0) remove(idx);
                      }}
                      onChange={(id, patch) => {
                        const idx = fields.findIndex((f) => f.id === id);
                        if (idx < 0) return;
                        if (patch.key !== undefined) setValue(`http_headers.${idx}.key`, patch.key);
                        if (patch.value !== undefined)
                          setValue(`http_headers.${idx}.value`, patch.value);
                      }}
                    />
                  </div>
                </div>
              </SettingsSection>

              {/* Protocol */}
              <SettingsSection
                title="Protocol"
                description="How packets flow between Tone and your server"
                icon={Cable}
                iconColor="text-violet-600 dark:text-violet-400"
                iconBg="bg-violet-50 dark:bg-violet-500/10"
                isOpen={openSections.protocol}
                onToggle={() => toggleSection('protocol')}
              >
                <Controller
                  name="transport_type"
                  control={control}
                  render={({ field }) => (
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ProtocolCard
                        selected={field.value === 'shttp'}
                        onSelect={() => field.onChange('shttp')}
                        title="Streamable HTTP"
                        description="Persistent connection with bidirectional streaming. Recommended for tool-calling agents."
                        diagram="shttp"
                        badge="Recommended"
                      />
                      <ProtocolCard
                        selected={field.value === 'sse'}
                        onSelect={() => field.onChange('sse')}
                        title="Server-Sent Events"
                        description="One-way push stream from server. Lightweight, best for read-only events."
                        diagram="sse"
                      />
                    </div>
                  )}
                />
              </SettingsSection>

              {/* Agents */}
              <SettingsSection
                title="Agents"
                description="Attach this MCP server to agents' live (published) versions"
                icon={Bot}
                iconColor="text-amber-600 dark:text-amber-400"
                iconBg="bg-amber-50 dark:bg-amber-500/10"
                isOpen={openSections.agents}
                onToggle={() => toggleSection('agents')}
              >
                <AgentAttachmentPicker
                  selectedIds={attachedAgentIds}
                  onChange={(ids) => {
                    setAttachedAgentIds(ids);
                    setAgentsTouched(true);
                  }}
                  loading={agentsLoading}
                  loadFailed={agentsLoadFailed}
                  entityLabel="MCP server"
                />
              </SettingsSection>

              {/* Status */}
              <SettingsSection
                title="Status"
                description="Enable or pause this MCP server for your agents"
                icon={Power}
                iconColor="text-emerald-600 dark:text-emerald-400"
                iconBg="bg-emerald-50 dark:bg-emerald-500/10"
                isOpen={openSections.status}
                onToggle={() => toggleSection('status')}
              >
                <Controller
                  name="is_active"
                  control={control}
                  render={({ field }) => (
                    <label
                      htmlFor="mcp-is-active"
                      className="flex cursor-pointer items-center justify-between gap-4"
                    >
                      <div className="min-w-0">
                        <p className="text-[13px] font-semibold text-foreground">
                          {field.value ? 'Server is active' : 'Server is paused'}
                        </p>
                        <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                          {field.value
                            ? 'Agents can route tool calls to this MCP server.'
                            : 'Agents will skip this server until you re-enable it.'}
                        </p>
                      </div>
                      <Switch
                        id="mcp-is-active"
                        checked={!!field.value}
                        onCheckedChange={(checked) => field.onChange(!!checked)}
                      />
                    </label>
                  )}
                />
              </SettingsSection>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ active, compact = false }: { active: boolean; compact?: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full text-[10px] font-medium',
        compact ? 'px-2 py-0.5' : 'px-2 py-0.5',
        active
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
          : 'bg-muted text-muted-foreground',
      )}
    >
      <span
        className={cn(
          'size-1.5 rounded-full',
          active ? 'animate-pulse bg-emerald-500' : 'bg-muted-foreground/50',
        )}
      />
      {active ? 'Active' : 'Paused'}
    </span>
  );
}

function Chip({ icon, label }: { icon?: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 px-2 py-0.5 text-[11px] font-medium text-foreground backdrop-blur dark:bg-background/40">
      {icon && <span className="text-muted-foreground">{icon}</span>}
      {label}
    </span>
  );
}

function RailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-foreground">{children}</dd>
    </div>
  );
}

function PreviewFavicon({
  hostname,
  size = 'md',
}: {
  hostname: string | null;
  size?: 'sm' | 'md';
}) {
  const [failed, setFailed] = useState(false);
  const url = getFaviconUrl(hostname);
  const show = !!url && !failed;
  const isSm = size === 'sm';
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border',
        isSm ? 'size-8' : 'size-9',
        show ? 'bg-white p-1 dark:border-border/60' : 'bg-primary/5 dark:bg-primary/10',
      )}
    >
      {show ? (
        <img
          src={url ?? ''}
          alt={hostname ?? 'MCP server icon'}
          width={isSm ? 18 : 20}
          height={isSm ? 18 : 20}
          className={cn('object-contain', isSm ? 'size-[18px]' : 'size-5')}
          onError={() => setFailed(true)}
        />
      ) : (
        <Boxes size={isSm ? 15 : 16} className="text-primary" />
      )}
    </div>
  );
}

function TimeoutDial({ value }: { value: number }) {
  const min = 1;
  const max = 300;
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const size = 132;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const arcSpan = c * 0.78;
  const arc = pct * arcSpan;

  return (
    <div className="relative mx-auto flex h-[132px] w-[132px] items-center justify-center">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-[130deg]"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="mcp-dial-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.55" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="1" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcSpan} ${c}`}
          className="text-border"
        />
        <g className="text-primary">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="url(#mcp-dial-gradient)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${arc} ${c}`}
            className="transition-all duration-300"
          />
        </g>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[30px] font-semibold leading-none tabular-nums tracking-tight text-foreground">
          {value}
        </span>
        <span className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
          seconds
        </span>
      </div>
    </div>
  );
}

function ProtocolCard({
  selected,
  onSelect,
  title,
  description,
  diagram,
  badge,
}: {
  selected: boolean;
  onSelect: () => void;
  title: string;
  description: string;
  diagram: 'shttp' | 'sse';
  badge?: string;
}) {
  return (
    <CustomButton
      type="text"
      onClick={onSelect}
      className={cn(
        '!h-auto !flex-col !items-stretch group relative flex flex-col gap-3 overflow-hidden rounded-lg border bg-background p-4 text-left transition-all',
        selected
          ? 'border-primary ring-2 ring-primary/25 shadow-sm'
          : 'border-border hover:border-primary/40 hover:bg-muted/20 hover:shadow-sm',
      )}
    >
      {selected && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-lg bg-gradient-to-br from-primary/[0.06] to-transparent"
        />
      )}

      <div className="relative flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-foreground">{title}</span>
          {badge && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9.5px] font-medium text-primary">
              <Sparkles size={9} />
              {badge}
            </span>
          )}
        </div>
        <span
          className={cn(
            'flex size-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
            selected ? 'border-primary bg-primary' : 'border-border bg-background',
          )}
        >
          {selected && <Check size={10} className="text-primary-foreground" strokeWidth={3} />}
        </span>
      </div>

      <ProtocolDiagram type={diagram} active={selected} />

      <p className="relative text-[12px] leading-relaxed text-muted-foreground">{description}</p>
    </CustomButton>
  );
}

function ProtocolDiagram({ type, active }: { type: 'shttp' | 'sse'; active: boolean }) {
  const gradientId = `mcp-proto-${type}`;
  return (
    <div
      className={cn(
        'rounded-md border bg-muted/30 px-3 py-2 transition-colors',
        active ? 'border-primary/30 text-primary' : 'border-border text-muted-foreground',
      )}
    >
      <svg viewBox="0 0 200 48" className="h-10 w-full" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.4" />
            <stop offset="50%" stopColor="currentColor" stopOpacity="1" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        <circle cx="20" cy="24" r="4" fill="currentColor" />
        <text
          x="20"
          y="44"
          textAnchor="middle"
          className="fill-current text-[8px] uppercase tracking-wider opacity-60"
        >
          srv
        </text>
        <circle cx="180" cy="24" r="4" fill="currentColor" />
        <text
          x="180"
          y="44"
          textAnchor="middle"
          className="fill-current text-[8px] uppercase tracking-wider opacity-60"
        >
          tone
        </text>

        {type === 'shttp' ? (
          <>
            <path
              d="M 28 24 Q 50 10 72 24 T 116 24 T 160 24 L 172 24"
              fill="none"
              stroke={active ? `url(#${gradientId})` : 'currentColor'}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <path
              d="M 28 24 Q 50 38 72 24 T 116 24 T 160 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              opacity="0.45"
              strokeDasharray="2,3"
            />
            <polygon points="172,24 168,21 168,27" fill="currentColor" />
            <polygon points="28,24 32,21 32,27" fill="currentColor" opacity="0.45" />
          </>
        ) : (
          <>
            <line
              x1="28"
              y1="24"
              x2="172"
              y2="24"
              stroke={active ? `url(#${gradientId})` : 'currentColor'}
              strokeWidth="1.5"
              strokeDasharray="6,5"
              strokeLinecap="round"
            />
            <circle cx="60" cy="24" r="2.5" fill="currentColor" />
            <circle cx="100" cy="24" r="2.5" fill="currentColor" />
            <circle cx="140" cy="24" r="2.5" fill="currentColor" />
            <polygon points="172,24 167,21 167,27" fill="currentColor" />
          </>
        )}
      </svg>
    </div>
  );
}

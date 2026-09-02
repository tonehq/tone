'use client';

import { Plus, Server, Settings2, Wrench, X } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { useAgentFormNav } from '@/components/agents/agent-form/AgentFormNav';
import AttachmentManagerModal, {
  type AttachmentManagerOption,
} from '@/components/agents/agent-form/AttachmentManagerModal';
import SectionCard from '@/components/agents/agent-form/SectionCard';
import { CustomButton } from '@/components/shared';
import { withAttachContext } from '@/utils/agentAttachmentContext';
import { Badge } from '@/components/ui/badge';
import { useToolsMcpCatalog } from '@/lib/api/toolsMcpCatalog';
import { useQueryErrorToast } from '@/lib/api/useQueryErrorToast';
import type { AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';

// Section accents. Kept small and re-used on both the section-header icon and
// the summary-row icon so the two categories read at a glance.
const TOOLS_ACCENT_ICON = 'bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-300';
const MCP_ACCENT_ICON = 'bg-sky-500/10 text-sky-700 ring-sky-500/30 dark:text-sky-300';

/** Toggle helper — flip an id in a string[] set. Shared between tools & MCP
 * so both sections agree on the semantics of "already selected". */
function toggleId(list: string[], id: string): string[] {
  const set = new Set(list);
  if (set.has(id)) set.delete(id);
  else set.add(id);
  return Array.from(set);
}

/** Auth types that can resolve credentials from a stored connection (OAuth,
 * custom bearer, OAuth2 client-credentials — all live in the same connection
 * store). The per-attachment connection picker is shown for these, or whenever
 * a default connection is already linked regardless of auth type. */
const CONNECTION_AUTH_TYPES: ReadonlySet<string> = new Set(['oauth', 'bearer', 'api_key']);

function supportsConnection(
  authType: string | null | undefined,
  connectionId: string | null | undefined,
): boolean {
  return (authType != null && CONNECTION_AUTH_TYPES.has(authType)) || connectionId != null;
}

/** Compact summary row shown OUTSIDE the modal for a currently-attached
 * tool / MCP. Displays the entity name, a connection chip when the attachment
 * resolves credentials from a stored connection, and a remove ``×``. All configuration
 * (add / remove / override) is done inside the modal — this row is a summary
 * of the current state so the section stays readable at a glance.
 */
function AttachmentSummaryRow({
  name,
  description,
  icon,
  iconClassName,
  oauthLabel,
  onRemove,
}: {
  name: string;
  description?: string | null;
  icon: ReactNode;
  iconClassName?: string;
  oauthLabel?: string | null;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-border/70 bg-background p-3">
      <div className="flex min-w-0 flex-1 items-start gap-2.5">
        <span
          className={cn(
            'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
            iconClassName ?? 'bg-muted ring-border text-muted-foreground',
          )}
        >
          {icon}
        </span>
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate text-sm font-medium text-foreground">{name}</span>
          {description && (
            <span className="line-clamp-1 text-xs text-muted-foreground">{description}</span>
          )}
          {oauthLabel && (
            <span className="mt-1 inline-flex w-fit items-center gap-1 rounded-full bg-muted/70 px-2 py-0.5 text-[11px] text-muted-foreground">
              Connection: {oauthLabel}
            </span>
          )}
        </div>
      </div>
      <CustomButton
        type="text"
        size="sm"
        onClick={onRemove}
        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
        aria-label={`Remove ${name}`}
      >
        <X className="size-3.5" />
      </CustomButton>
    </div>
  );
}

/** Skeleton rows shown while the tool/MCP catalog loads. The selected ids are
 * known immediately (form state) but their names/descriptions come from the
 * catalog fetch, so without this the attached rows flash empty under the
 * "N selected" badge. Row count mirrors the selection so layout stays stable. */
function AttachmentSkeletonList({ count }: { count: number }) {
  return (
    <div className="grid gap-2" aria-hidden>
      {Array.from({ length: Math.max(1, count) }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-2.5 rounded-xl border border-border/70 bg-background p-3"
        >
          <div className="size-7 shrink-0 animate-pulse rounded-lg bg-muted" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3.5 w-1/3 animate-pulse rounded bg-muted" />
            <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Placeholder shown when nothing is attached — same layout for both sections. */
function EmptyAttached({ label, onManage }: { label: string; onManage: () => void }) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-dashed border-border/70 px-4 py-6 text-center">
      <p className="text-xs text-muted-foreground">
        No {label} attached. Use <span className="font-medium">Manage {label}</span> to pick from
        your catalog.
      </p>
      <CustomButton
        type="default"
        size="sm"
        icon={<Settings2 className="size-3.5" />}
        onClick={onManage}
      >
        Manage {label}
      </CustomButton>
    </div>
  );
}

export default function ToolsMcpStep() {
  const { safeNavigate } = useAgentFormNav();
  const { agentId, detail } = useAgentEditor();
  const { control, setValue } = useFormContext<AgentFormState>();

  // Once the agent + its currently-viewed version are known, redirect the
  // "New tool" / "New MCP server" buttons through /tools/create and
  // /mcp/create with an attach context so the create page can wire the new
  // row onto THIS version and bounce back — no manual re-attach step.
  const attachCtx = agentId && detail?.config?.id ? { agentId, configId: detail.config.id } : null;
  const newToolHref = attachCtx ? withAttachContext('/tools/create', attachCtx) : '/tools/create';
  const newMcpHref = attachCtx ? withAttachContext('/mcp/create', attachCtx) : '/mcp/create';
  const selectedToolIds = useWatch({ control, name: 'tool_ids' }) ?? [];
  const selectedMcpIds = useWatch({ control, name: 'mcp_server_ids' }) ?? [];
  const toolOverrides = useWatch({ control, name: 'tool_oauth_overrides' }) ?? {};
  const mcpOverrides = useWatch({ control, name: 'mcp_server_oauth_overrides' }) ?? {};

  const [toolsModalOpen, setToolsModalOpen] = useState(false);
  const [mcpModalOpen, setMcpModalOpen] = useState(false);

  // Tools + MCP servers + OAuth connections load as one catalog (single loading
  // flag; any failure blanks all three + toasts, same as the old Promise.all).
  // `addConnection` prepends an inline-created credential to the cached list.
  const { data, isLoading: loading, error, addConnection } = useToolsMcpCatalog();
  const tools = useMemo(() => data?.tools ?? [], [data]);
  const mcpServers = useMemo(() => data?.mcpServers ?? [], [data]);
  const oauthConnections = useMemo(() => data?.connections ?? [], [data]);
  useQueryErrorToast(error);

  // Lookups by id — iterating over ``selected*Ids`` (source of truth) and
  // reading from these maps avoids the O(n²) ``find`` per selected row.
  const toolById = useMemo(() => new Map(tools.map((t) => [t.id, t])), [tools]);
  const mcpById = useMemo(() => new Map(mcpServers.map((m) => [m.id, m])), [mcpServers]);
  const connectionById = useMemo(
    () => new Map(oauthConnections.map((c) => [c.id, c])),
    [oauthConnections],
  );

  const toggleTool = (toolId: string) =>
    setValue('tool_ids', toggleId(selectedToolIds, toolId), { shouldDirty: true });
  const toggleMcp = (mcpId: string) =>
    setValue('mcp_server_ids', toggleId(selectedMcpIds, mcpId), { shouldDirty: true });

  // Stores ``null`` on "Use default" instead of removing the entry so the
  // diff-aware update payload can tell the backend to clear a previously-set
  // override. Deleting the key would make the clear invisible to the diff.
  const setToolOverride = (toolId: string, next: string | null) =>
    setValue('tool_oauth_overrides', { ...toolOverrides, [toolId]: next }, { shouldDirty: true });
  const setMcpOverride = (mcpId: string, next: string | null) =>
    setValue(
      'mcp_server_oauth_overrides',
      { ...mcpOverrides, [mcpId]: next },
      { shouldDirty: true },
    );

  // Project raw tools/MCPs into the modal option shape once — the modal is
  // agnostic to the underlying entity type.
  const toolOptions: AttachmentManagerOption[] = useMemo(
    () =>
      tools.map((t) => ({
        id: t.id,
        name: t.name,
        description: t.description,
        supportsConnection: supportsConnection(t.auth_type, t.oauth_connection_id),
        defaultConnectionId: t.oauth_connection_id,
      })),
    [tools],
  );
  const mcpOptions: AttachmentManagerOption[] = useMemo(
    () =>
      mcpServers.map((m) => ({
        id: m.id,
        name: m.name,
        description: m.description,
        supportsConnection: supportsConnection(m.auth_type, m.oauth_connection_id),
        defaultConnectionId: m.oauth_connection_id ?? null,
      })),
    [mcpServers],
  );

  /** Human-readable label for the connection currently in use for an
   * attachment. Prefers the override, falls back to the entity default. */
  const oauthLabelFor = (
    overrideId: string | null | undefined,
    defaultId: string | null | undefined,
  ): string | null => {
    const effectiveId = overrideId ?? defaultId ?? null;
    if (!effectiveId) return null;
    const conn = connectionById.get(effectiveId);
    if (!conn) return null;
    // Same shape the MCP / Tool edit pages use: "<user_email> (<provider_slug>)"
    // — falls back through label / slug so a connection without a stored email
    // still renders something meaningful.
    return `${conn.public_metadata?.user_email || conn.label || conn.provider_slug} (${conn.provider_slug})`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* ─── Tools ──────────────────────────────────────────────────────── */}
      <SectionCard
        icon={<Wrench className="size-3.5" strokeWidth={2.25} />}
        tone="amber"
        title="Tools"
        description="Direct function calls available to the agent."
        action={
          <div className="flex items-center gap-2">
            {selectedToolIds.length > 0 && (
              <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
                {selectedToolIds.length} selected
              </Badge>
            )}
            <CustomButton
              type="default"
              size="sm"
              icon={<Settings2 className="size-3.5" />}
              onClick={() => setToolsModalOpen(true)}
            >
              Manage tools
            </CustomButton>
            <CustomButton
              type="default"
              size="sm"
              icon={<Plus className="size-3.5" />}
              onClick={() => safeNavigate(newToolHref)}
            >
              New tool
            </CustomButton>
          </div>
        }
      >
        {loading ? (
          <AttachmentSkeletonList count={selectedToolIds.length} />
        ) : selectedToolIds.length === 0 ? (
          <EmptyAttached label="tools" onManage={() => setToolsModalOpen(true)} />
        ) : (
          <div className="grid gap-2">
            {selectedToolIds.map((toolId) => {
              const tool = toolById.get(toolId);
              if (!tool) return null;
              return (
                <AttachmentSummaryRow
                  key={tool.id}
                  name={tool.name}
                  description={tool.description}
                  icon={<Wrench className="size-3.5" />}
                  iconClassName={TOOLS_ACCENT_ICON}
                  oauthLabel={
                    supportsConnection(tool.auth_type, tool.oauth_connection_id)
                      ? oauthLabelFor(toolOverrides[tool.id], tool.oauth_connection_id)
                      : null
                  }
                  onRemove={() => toggleTool(tool.id)}
                />
              );
            })}
          </div>
        )}
      </SectionCard>

      {/* ─── MCP servers ────────────────────────────────────────────────── */}
      <SectionCard
        icon={<Server className="size-3.5" strokeWidth={2.25} />}
        tone="sky"
        title="MCP servers"
        description="Hosted toolsets the agent can reach."
        action={
          <div className="flex items-center gap-2">
            {selectedMcpIds.length > 0 && (
              <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
                {selectedMcpIds.length} attached
              </Badge>
            )}
            <CustomButton
              type="default"
              size="sm"
              icon={<Settings2 className="size-3.5" />}
              onClick={() => setMcpModalOpen(true)}
            >
              Manage MCP servers
            </CustomButton>
            <CustomButton
              type="default"
              size="sm"
              icon={<Plus className="size-3.5" />}
              onClick={() => safeNavigate(newMcpHref)}
            >
              New MCP server
            </CustomButton>
          </div>
        }
      >
        {loading ? (
          <AttachmentSkeletonList count={selectedMcpIds.length} />
        ) : selectedMcpIds.length === 0 ? (
          <EmptyAttached label="MCP servers" onManage={() => setMcpModalOpen(true)} />
        ) : (
          <div className="grid gap-2">
            {selectedMcpIds.map((mcpId) => {
              const server = mcpById.get(mcpId);
              if (!server) return null;
              return (
                <AttachmentSummaryRow
                  key={server.id}
                  name={server.name}
                  description={server.description}
                  icon={<Server className="size-3.5" />}
                  iconClassName={MCP_ACCENT_ICON}
                  oauthLabel={
                    supportsConnection(server.auth_type, server.oauth_connection_id)
                      ? oauthLabelFor(mcpOverrides[server.id], server.oauth_connection_id)
                      : null
                  }
                  onRemove={() => toggleMcp(server.id)}
                />
              );
            })}
          </div>
        )}
      </SectionCard>

      {/* ─── Manager modals ─────────────────────────────────────────────── */}
      <AttachmentManagerModal
        open={toolsModalOpen}
        onClose={() => setToolsModalOpen(false)}
        title="Manage tools"
        description="Pick the tools this version of the agent can call, and choose the OAuth connection each one should use."
        searchPlaceholder="Search tools by name or description..."
        options={toolOptions}
        selectedIds={selectedToolIds}
        overrides={toolOverrides}
        connections={oauthConnections}
        loading={loading}
        rowIcon={<Wrench className="size-3.5" />}
        rowIconClassName={TOOLS_ACCENT_ICON}
        onToggle={toggleTool}
        onOverrideChange={setToolOverride}
        onConnectionCreated={addConnection}
      />

      <AttachmentManagerModal
        open={mcpModalOpen}
        onClose={() => setMcpModalOpen(false)}
        title="Manage MCP servers"
        description="Pick which MCP servers this agent version can reach, and choose an OAuth connection per server if needed."
        searchPlaceholder="Search MCP servers by name or description..."
        options={mcpOptions}
        selectedIds={selectedMcpIds}
        overrides={mcpOverrides}
        connections={oauthConnections}
        loading={loading}
        rowIcon={<Server className="size-3.5" />}
        rowIconClassName={MCP_ACCENT_ICON}
        onToggle={toggleMcp}
        onOverrideChange={setMcpOverride}
        onConnectionCreated={addConnection}
      />
    </div>
  );
}

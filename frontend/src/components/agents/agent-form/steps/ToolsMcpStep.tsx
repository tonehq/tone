'use client';

import { Plus, Server, Settings2, Wrench, X } from 'lucide-react';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { useAgentFormNav } from '@/components/agents/agent-form/AgentFormNav';
import AttachmentManagerModal, {
  type AttachmentManagerOption,
} from '@/components/agents/agent-form/AttachmentManagerModal';
import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CustomButton } from '@/components/shared';
import { withAttachContext } from '@/utils/agentAttachmentContext';
import { Badge } from '@/components/ui/badge';
import { listMcpServers } from '@/services/mcpServerService';
import { listOAuthConnections } from '@/services/oauthService';
import { getAllTools } from '@/services/toolService';
import type { AgentFormState } from '@/types/agent';
import type { MCPServer } from '@/types/mcp';
import type { OAuthConnection } from '@/types/oauth';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

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

/** Compact summary row shown OUTSIDE the modal for a currently-attached
 * tool / MCP. Displays the entity name, an OAuth connection chip when the
 * attachment authenticates via OAuth, and a remove ``×``. All configuration
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
              OAuth: {oauthLabel}
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

  const [tools, setTools] = useState<Tool[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  // Loaded once so the OAuth picker inside the modal doesn't do per-row fetches.
  const [oauthConnections, setOauthConnections] = useState<OAuthConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [toolsModalOpen, setToolsModalOpen] = useState(false);
  const [mcpModalOpen, setMcpModalOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getAllTools(), listMcpServers(), listOAuthConnections()])
      .then(([toolRows, mcpRows, connectionRows]) => {
        if (cancelled) return;
        setTools(toolRows);
        setMcpServers(mcpRows);
        setOauthConnections(connectionRows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
        usesOAuth: t.auth_type === 'oauth' || !!t.oauth_connection_id,
        defaultConnectionId: t.oauth_connection_id,
        appIntegrationId: t.app_integration_id ?? null,
      })),
    [tools],
  );
  const mcpOptions: AttachmentManagerOption[] = useMemo(
    () =>
      mcpServers.map((m) => ({
        id: m.id,
        name: m.name,
        description: m.description,
        usesOAuth: !!m.oauth_connection_id,
        defaultConnectionId: m.oauth_connection_id ?? null,
        appIntegrationId: m.app_integration_id ?? null,
      })),
    [mcpServers],
  );

  /** Human-readable label for the OAuth connection currently in use for an
   * attachment. Prefers the override, falls back to the entity default. */
  const oauthLabelFor = (
    overrideId: string | null | undefined,
    defaultId: string | null | undefined,
  ): string | null => {
    const effectiveId = overrideId ?? defaultId ?? null;
    if (!effectiveId) return null;
    const conn = connectionById.get(effectiveId);
    const label = conn?.label || conn?.provider_slug || 'connected account';
    return overrideId ? label : `${label} (default)`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* ─── Tools ──────────────────────────────────────────────────────── */}
      <SectionCard
        icon={<Wrench className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.amber}
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
        {selectedToolIds.length === 0 ? (
          <EmptyAttached label="tools" onManage={() => setToolsModalOpen(true)} />
        ) : (
          <div className="grid gap-2">
            {selectedToolIds.map((toolId) => {
              const tool = toolById.get(toolId);
              if (!tool) return null;
              const usesOAuth = tool.auth_type === 'oauth' || !!tool.oauth_connection_id;
              return (
                <AttachmentSummaryRow
                  key={tool.id}
                  name={tool.name}
                  description={tool.description}
                  icon={<Wrench className="size-3.5" />}
                  iconClassName={TOOLS_ACCENT_ICON}
                  oauthLabel={
                    usesOAuth
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
        iconClassName={ACCENTS.sky}
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
        {selectedMcpIds.length === 0 ? (
          <EmptyAttached label="MCP servers" onManage={() => setMcpModalOpen(true)} />
        ) : (
          <div className="grid gap-2">
            {selectedMcpIds.map((mcpId) => {
              const server = mcpById.get(mcpId);
              if (!server) return null;
              const usesOAuth = !!server.oauth_connection_id;
              return (
                <AttachmentSummaryRow
                  key={server.id}
                  name={server.name}
                  description={server.description}
                  icon={<Server className="size-3.5" />}
                  iconClassName={MCP_ACCENT_ICON}
                  oauthLabel={
                    usesOAuth
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
      />
    </div>
  );
}

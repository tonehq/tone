'use client';

import { Check, Plus, Server, Sparkles, Wrench, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentFormNav } from '@/components/agents/agent-form/AgentFormNav';
import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CustomButton, SearchBar, SelectInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listMcpServers } from '@/services/mcpServerService';
import { getAllTools } from '@/services/toolService';
import type { AgentFormState } from '@/types/agent';
import type { MCPServer } from '@/types/mcp';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

// Per-section accent so the two distinct categories read at a glance.
const TOOLS_ACCENT = {
  ring: 'ring-amber-500/30',
  bg: 'bg-amber-500/10',
  text: 'text-amber-700 dark:text-amber-300',
  selected: 'border-amber-500/60 bg-amber-500/5 ring-1 ring-amber-500/20',
};
const MCP_ACCENT = {
  ring: 'ring-sky-500/30',
  bg: 'bg-sky-500/10',
  text: 'text-sky-700 dark:text-sky-300',
};

export default function ToolsMcpStep() {
  const { safeNavigate } = useAgentFormNav();
  const { control, setValue } = useFormContext<AgentFormState>();
  const selectedToolIds = useWatch({ control, name: 'tool_ids' }) ?? [];
  const selectedMcpIds = useWatch({ control, name: 'mcp_server_ids' }) ?? [];

  const [tools, setTools] = useState<Tool[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [toolSearch, setToolSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getAllTools(), listMcpServers()])
      .then(([toolRows, mcpRows]) => {
        if (cancelled) return;
        setTools(toolRows);
        setMcpServers(mcpRows);
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

  const filteredTools = useMemo(() => {
    const q = toolSearch.trim().toLowerCase();
    if (!q) return tools;
    return tools.filter(
      (t) =>
        t.name.toLowerCase().includes(q) || (t.description?.toLowerCase().includes(q) ?? false),
    );
  }, [tools, toolSearch]);

  const toggleTool = (toolId: string) => {
    const set = new Set(selectedToolIds);
    if (set.has(toolId)) set.delete(toolId);
    else set.add(toolId);
    setValue('tool_ids', Array.from(set), { shouldDirty: true });
  };

  const clearSelectedTools = () => {
    setValue('tool_ids', [], { shouldDirty: true });
  };

  const mcpServerOptions = useMemo(
    () => mcpServers.map((m) => ({ value: m.id, label: m.name })),
    [mcpServers],
  );

  const availableMcpToAdd = useMemo(() => {
    const used = new Set(selectedMcpIds);
    return mcpServerOptions.filter((opt) => !used.has(opt.value));
  }, [mcpServerOptions, selectedMcpIds]);

  const addMcpServer = (mcpServerId: string) => {
    if (!mcpServerId || selectedMcpIds.includes(mcpServerId)) return;
    setValue('mcp_server_ids', [...selectedMcpIds, mcpServerId], { shouldDirty: true });
  };

  const removeMcpServer = (mcpServerId: string) => {
    setValue(
      'mcp_server_ids',
      selectedMcpIds.filter((id) => id !== mcpServerId),
      { shouldDirty: true },
    );
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
            {selectedToolIds.length > 0 && (
              <CustomButton
                type="text"
                size="sm"
                onClick={clearSelectedTools}
                className="text-xs text-muted-foreground hover:text-destructive"
              >
                Clear
              </CustomButton>
            )}
            <CustomButton
              type="default"
              size="sm"
              icon={<Plus className="size-3.5" />}
              onClick={() => safeNavigate('/tools/create')}
            >
              New tool
            </CustomButton>
          </div>
        }
      >
        {/* Search */}
        <SearchBar
          placeholder="Search tools by name or description..."
          value={toolSearch}
          onSearch={setToolSearch}
          debounceMs={200}
        />

        {/* Body */}
        {loading ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-[56px] animate-pulse rounded-xl border border-border/40 bg-muted/40"
              />
            ))}
          </div>
        ) : filteredTools.length === 0 ? (
          <div className="flex flex-col items-center gap-1.5 rounded-xl border border-dashed border-border/70 px-6 py-5 text-center">
            <span
              className={cn(
                'flex size-8 items-center justify-center rounded-lg ring-1 ring-inset',
                TOOLS_ACCENT.bg,
                TOOLS_ACCENT.ring,
                TOOLS_ACCENT.text,
              )}
            >
              <Sparkles className="size-3.5" />
            </span>
            {toolSearch ? (
              <p className="text-sm text-muted-foreground">
                Nothing matches &ldquo;{toolSearch}&rdquo;.
              </p>
            ) : (
              <>
                <p className="text-sm font-medium text-foreground">No tools yet</p>
                <p className="max-w-sm text-xs text-muted-foreground">
                  Create your first tool to give this agent something to do beyond chat.
                </p>
                <CustomButton
                  type="primary"
                  size="sm"
                  icon={<Plus className="size-3.5" />}
                  onClick={() => safeNavigate('/tools/create')}
                  className="mt-1"
                >
                  Create a tool
                </CustomButton>
              </>
            )}
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {filteredTools.map((tool) => {
              const selected = selectedToolIds.includes(tool.id);
              return (
                <CustomButton
                  key={tool.id}
                  type="text"
                  onClick={() => toggleTool(tool.id)}
                  className={cn(
                    'group flex h-auto items-start justify-between gap-3 rounded-xl border p-3 text-left transition-all',
                    selected
                      ? TOOLS_ACCENT.selected
                      : 'border-border/70 hover:-translate-y-px hover:border-border hover:bg-muted/30',
                  )}
                >
                  <div className="flex min-w-0 flex-1 items-start gap-2.5">
                    <span
                      className={cn(
                        'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset transition-colors',
                        selected
                          ? cn(TOOLS_ACCENT.bg, TOOLS_ACCENT.ring, TOOLS_ACCENT.text)
                          : 'bg-muted ring-border text-muted-foreground',
                      )}
                    >
                      <Wrench className="size-3.5" />
                    </span>
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="truncate text-sm font-medium text-foreground">
                        {tool.name}
                      </span>
                      {tool.description && (
                        <span className="line-clamp-2 text-xs text-muted-foreground">
                          {tool.description}
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className={cn(
                      'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors',
                      selected
                        ? 'border-amber-500 bg-amber-500 text-white'
                        : 'border-border bg-background text-transparent',
                    )}
                  >
                    <Check className="size-3" />
                  </span>
                </CustomButton>
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
              icon={<Plus className="size-3.5" />}
              onClick={() => safeNavigate('/mcp/create')}
            >
              New MCP server
            </CustomButton>
          </div>
        }
      >
        {/* Attached servers */}
        {selectedMcpIds.length === 0 ? (
          <div className="flex flex-col items-center gap-1.5 rounded-xl border border-dashed border-border/70 px-6 py-5 text-center">
            <span
              className={cn(
                'flex size-8 items-center justify-center rounded-lg ring-1 ring-inset',
                MCP_ACCENT.bg,
                MCP_ACCENT.ring,
                MCP_ACCENT.text,
              )}
            >
              <Server className="size-3.5" />
            </span>
            <p className="text-sm font-medium text-foreground">
              {availableMcpToAdd.length === 0 ? 'No MCP servers available' : 'No servers attached'}
            </p>
            <p className="max-w-sm text-xs text-muted-foreground">
              {availableMcpToAdd.length === 0
                ? 'Create one to start attaching hosted toolsets to your agents.'
                : 'Pick one from the dropdown below to give this agent extra capabilities.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {selectedMcpIds.map((mcpServerId) => {
              const server = mcpServers.find((m) => m.id === mcpServerId);
              return (
                <div
                  key={mcpServerId}
                  className="flex items-start justify-between gap-3 rounded-xl border border-border/70 bg-background p-3 transition-shadow hover:shadow-sm"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className={cn(
                        'flex size-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
                        MCP_ACCENT.bg,
                        MCP_ACCENT.ring,
                        MCP_ACCENT.text,
                      )}
                    >
                      <Server className="size-3.5" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {server?.name ?? 'Unknown MCP server'}
                      </p>
                      {server?.description && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                          {server.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => removeMcpServer(mcpServerId)}
                    aria-label={`Remove ${server?.name ?? 'server'}`}
                    className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  >
                    <X className="size-4" />
                  </CustomButton>
                </div>
              );
            })}
          </div>
        )}

        {/* Attach control */}
        {availableMcpToAdd.length > 0 && (
          <div className="flex flex-col gap-1.5 rounded-xl border border-dashed border-border/70 bg-muted/20 p-3">
            <p className="text-[11px] font-medium text-muted-foreground">
              Attach an existing server
            </p>
            <SelectInput
              name="add_mcp_server"
              options={availableMcpToAdd}
              value=""
              onValueChange={addMcpServer}
              placeholder="Pick a server to add…"
              loading={loading}
            />
          </div>
        )}
      </SectionCard>
    </div>
  );
}

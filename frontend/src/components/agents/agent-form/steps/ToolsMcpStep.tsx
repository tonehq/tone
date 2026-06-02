'use client';

import { Check, Plus, Server, Sparkles, Wrench } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { useAgentFormNav } from '@/components/agents/agent-form/AgentFormNav';
import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import { CustomButton, SearchBar } from '@/components/shared';
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
  selected: 'border-sky-500/60 bg-sky-500/5 ring-1 ring-sky-500/20',
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
  const [mcpSearch, setMcpSearch] = useState('');

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

  const filteredMcpServers = useMemo(() => {
    const q = mcpSearch.trim().toLowerCase();
    if (!q) return mcpServers;
    return mcpServers.filter(
      (m) =>
        m.name.toLowerCase().includes(q) || (m.description?.toLowerCase().includes(q) ?? false),
    );
  }, [mcpServers, mcpSearch]);

  const toggleMcp = (mcpServerId: string) => {
    const set = new Set(selectedMcpIds);
    if (set.has(mcpServerId)) set.delete(mcpServerId);
    else set.add(mcpServerId);
    setValue('mcp_server_ids', Array.from(set), { shouldDirty: true });
  };

  const clearSelectedMcp = () => {
    setValue('mcp_server_ids', [], { shouldDirty: true });
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
            {selectedMcpIds.length > 0 && (
              <CustomButton
                type="text"
                size="sm"
                onClick={clearSelectedMcp}
                className="text-xs text-muted-foreground hover:text-destructive"
              >
                Clear
              </CustomButton>
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
        {/* Search */}
        <SearchBar
          placeholder="Search MCP servers by name or description..."
          value={mcpSearch}
          onSearch={setMcpSearch}
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
        ) : filteredMcpServers.length === 0 ? (
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
            {mcpSearch ? (
              <p className="text-sm text-muted-foreground">
                Nothing matches &ldquo;{mcpSearch}&rdquo;.
              </p>
            ) : (
              <>
                <p className="text-sm font-medium text-foreground">No MCP servers yet</p>
                <p className="max-w-sm text-xs text-muted-foreground">
                  Create one to start attaching hosted toolsets to your agents.
                </p>
                <CustomButton
                  type="primary"
                  size="sm"
                  icon={<Plus className="size-3.5" />}
                  onClick={() => safeNavigate('/mcp/create')}
                  className="mt-1"
                >
                  Create an MCP server
                </CustomButton>
              </>
            )}
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {filteredMcpServers.map((server) => {
              const selected = selectedMcpIds.includes(server.id);
              return (
                <CustomButton
                  key={server.id}
                  type="text"
                  onClick={() => toggleMcp(server.id)}
                  className={cn(
                    'group flex h-auto items-start justify-between gap-3 rounded-xl border p-3 text-left transition-all',
                    selected
                      ? MCP_ACCENT.selected
                      : 'border-border/70 hover:-translate-y-px hover:border-border hover:bg-muted/30',
                  )}
                >
                  <div className="flex min-w-0 flex-1 items-start gap-2.5">
                    <span
                      className={cn(
                        'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset transition-colors',
                        selected
                          ? cn(MCP_ACCENT.bg, MCP_ACCENT.ring, MCP_ACCENT.text)
                          : 'bg-muted ring-border text-muted-foreground',
                      )}
                    >
                      <Server className="size-3.5" />
                    </span>
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="truncate text-sm font-medium text-foreground">
                        {server.name}
                      </span>
                      {server.description && (
                        <span className="line-clamp-2 text-xs text-muted-foreground">
                          {server.description}
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className={cn(
                      'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors',
                      selected
                        ? 'border-sky-500 bg-sky-500 text-white'
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
    </div>
  );
}

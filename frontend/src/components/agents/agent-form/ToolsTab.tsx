'use client';

import { fetchToolsAtom, toolsAtom } from '@/atoms/ToolAtom';
import { CustomButton } from '@/components/shared';
import type { Tool } from '@/types/tool';
import { attachToolToAgents, detachToolFromAgents, getToolsByAgent } from '@/services/toolService';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Link2Off, Plus, Wrench } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import ToolPickerModal from './ToolPickerModal';

interface ToolsTabProps {
  agentId?: string;
  isEditMode: boolean;
}

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-500/15 text-emerald-600',
  POST: 'bg-blue-500/15 text-blue-600',
  PUT: 'bg-amber-500/15 text-amber-600',
  DELETE: 'bg-red-500/15 text-red-600',
  PATCH: 'bg-violet-500/15 text-violet-600',
};

export default function ToolsTab({ agentId, isEditMode }: ToolsTabProps) {
  const [{ tools: allTools }] = useAtom(toolsAtom);
  const [, fetchAllTools] = useAtom(fetchToolsAtom);

  const [attachedTools, setAttachedTools] = useState<Tool[]>([]);
  const [loadingAttached, setLoadingAttached] = useState(false);
  const [detachingToolId, setDetachingToolId] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const loadAttachedTools = useCallback(async () => {
    if (!agentId) return;
    setLoadingAttached(true);
    try {
      const tools = await getToolsByAgent(agentId);
      setAttachedTools(tools);
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoadingAttached(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchAllTools().catch(handleApiError);
  }, [fetchAllTools]);

  useEffect(() => {
    if (isEditMode && agentId) {
      loadAttachedTools();
    }
  }, [isEditMode, agentId, loadAttachedTools]);

  const handleAttach = useCallback(
    async (toolIds: string[]) => {
      if (!agentId) return;
      try {
        for (const toolId of toolIds) {
          await attachToolToAgents({ tool_id: toolId, agent_ids: [agentId] });
        }
        showToast.success(`${toolIds.length} tool(s) attached successfully`);
        await loadAttachedTools();
      } catch (error) {
        handleApiError(error);
        throw error;
      }
    },
    [agentId, loadAttachedTools],
  );

  const handleDetach = useCallback(
    async (tool: Tool) => {
      if (!agentId) return;
      setDetachingToolId(tool.id);
      try {
        await detachToolFromAgents({ tool_id: tool.id, agent_ids: [agentId] });
        showToast.success(`"${tool.name}" detached successfully`);
        setAttachedTools((prev) => prev.filter((t) => t.id !== tool.id));
      } catch (error) {
        handleApiError(error);
      } finally {
        setDetachingToolId(null);
      }
    },
    [agentId],
  );

  if (!isEditMode) {
    return (
      <div className="space-y-5">
        <div className="rounded-xl border border-border bg-background shadow-sm">
          <div className="flex items-center gap-3 border-b border-border/60 px-5 py-3.5">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Wrench size={16} className="text-primary" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Tools</h2>
              <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                External APIs your agent can call during conversations.
              </p>
            </div>
          </div>
          <div className="flex flex-col items-center justify-center px-5 py-12 text-center">
            <div className="flex size-12 items-center justify-center rounded-xl bg-muted/50">
              <Wrench size={20} className="text-muted-foreground" />
            </div>
            <p className="mt-3 text-[13px] font-medium text-foreground">Save the agent first</p>
            <p className="mt-1 text-[12px] text-muted-foreground">
              You can attach tools after saving the agent.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border bg-background shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Wrench size={16} className="text-primary" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Tools</h2>
              <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                External APIs your agent can call during conversations.
              </p>
            </div>
          </div>
          <CustomButton
            type="primary"
            icon={<Plus size={14} />}
            onClick={() => setPickerOpen(true)}
          >
            Add Tool
          </CustomButton>
        </div>

        {/* Content */}
        <div className="px-5 py-4">
          {loadingAttached && (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          )}

          {!loadingAttached && attachedTools.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="flex size-12 items-center justify-center rounded-xl bg-muted/50">
                <Wrench size={20} className="text-muted-foreground" />
              </div>
              <p className="mt-3 text-[13px] font-medium text-foreground">No tools attached</p>
              <p className="mt-1 text-[12px] text-muted-foreground">
                Click &quot;Add Tool&quot; to give your agent the ability to call external APIs.
              </p>
            </div>
          )}

          {!loadingAttached && attachedTools.length > 0 && (
            <div className="divide-y divide-border/40">
              {attachedTools.map((tool) => {
                const m = tool.method?.toUpperCase() ?? 'POST';
                return (
                  <div key={tool.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-[13px] font-medium text-foreground">
                          {tool.name}
                        </span>
                        <span
                          className={cn(
                            'shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold',
                            METHOD_COLORS[m] ?? 'bg-muted text-muted-foreground',
                          )}
                        >
                          {m}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
                        {tool.description}
                      </p>
                    </div>
                    <CustomButton
                      type="default"
                      size="sm"
                      icon={<Link2Off size={12} />}
                      onClick={() => handleDetach(tool)}
                      loading={detachingToolId === tool.id}
                      disabled={detachingToolId !== null}
                      className="shrink-0 text-[12px]"
                    >
                      Detach
                    </CustomButton>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Picker Modal */}
      <ToolPickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        allTools={allTools}
        attachedToolIds={attachedTools.map((t) => t.id)}
        onAttach={handleAttach}
      />
    </div>
  );
}

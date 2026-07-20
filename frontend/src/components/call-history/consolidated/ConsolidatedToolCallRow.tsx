'use client';

import { CustomButton } from '@/components/shared';
import {
  formatDuration as formatToolDuration,
  durationToneClass,
  prettyJson,
  statusPill,
  toolTypeChipClasses,
  toolTypeLabel,
} from '@/components/call-history/tools-mcp/helpers';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { ToolExecution } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import React, { useState } from 'react';

function formatTimestampMs(ts: string | null): string {
  if (!ts) return '-';
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return '-';
  const date = d.toLocaleDateString();
  const time = d.toLocaleTimeString(undefined, { hour12: false });
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  return `${date}, ${time}.${ms}`;
}

interface ConsolidatedToolCallRowProps {
  tool: ToolExecution;
}

/**
 * One tool invocation inside a consolidated turn. Renders as a compact row
 * with a header (name / type chip / status pill / duration) and two
 * independently collapsible payloads (arguments + result). Keeps args + result
 * inline rather than opening a drawer so users can eyeball a whole turn — the
 * dedicated Tool & MCP tab still exists for deep inspection.
 */
const ConsolidatedToolCallRow: React.FC<ConsolidatedToolCallRowProps> = ({ tool }) => {
  const [argsOpen, setArgsOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);

  const duration = formatToolDuration(tool.duration_ms);
  const status = statusPill(tool.status);
  const typeLabel = toolTypeLabel(tool.tool_type);
  const typeChip = toolTypeChipClasses(tool.tool_type);

  const hasArgs = tool.arguments != null && tool.arguments !== '';
  const hasResult = tool.result != null && tool.result !== '';
  const hasError = !!tool.error_message;

  return (
    <div className="rounded-lg border border-border/70 bg-background/60 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <Wrench className="size-3.5" />
        </span>
        <span className="truncate text-sm font-medium text-foreground">
          {tool.tool_name || 'Unnamed tool'}
        </span>
        {tool.tool_type && (
          <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', typeChip)}>
            {typeLabel}
          </span>
        )}
        <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', status.className)}>
          {status.label}
        </span>
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className={cn(
                  'ml-auto cursor-pointer text-xs tabular-nums',
                  durationToneClass(duration.tone),
                )}
              >
                {duration.text}
              </span>
            </TooltipTrigger>
            <TooltipContent side="left" className="px-3 py-2">
              <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-1 text-[11px]">
                <span className="text-background/70">Proposed at</span>
                <span className="tabular-nums">{formatTimestampMs(tool.proposed_at)}</span>
                <span className="text-background/70">Invoked at</span>
                <span className="tabular-nums">{formatTimestampMs(tool.invoked_at)}</span>
                <span className="text-background/70">Completed at</span>
                <span className="tabular-nums">{formatTimestampMs(tool.completed_at)}</span>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {(hasArgs || hasResult || hasError) && (
        <div className="mt-2 flex flex-wrap gap-2">
          {hasArgs && (
            <CustomButton
              type="text"
              size="xs"
              onClick={() => setArgsOpen((v) => !v)}
              icon={
                argsOpen ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />
              }
              className="h-6 rounded-md px-2 text-[11px] text-muted-foreground hover:text-foreground"
            >
              Arguments
            </CustomButton>
          )}
          {hasResult && (
            <CustomButton
              type="text"
              size="xs"
              onClick={() => setResultOpen((v) => !v)}
              icon={
                resultOpen ? (
                  <ChevronDown className="size-3" />
                ) : (
                  <ChevronRight className="size-3" />
                )
              }
              className="h-6 rounded-md px-2 text-[11px] text-muted-foreground hover:text-foreground"
            >
              Result
            </CustomButton>
          )}
        </div>
      )}

      {argsOpen && hasArgs && (
        <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted/60 p-2 font-mono text-[11px] leading-relaxed text-foreground/90">
          {prettyJson(tool.arguments)}
        </pre>
      )}
      {resultOpen && hasResult && (
        <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted/60 p-2 font-mono text-[11px] leading-relaxed text-foreground/90">
          {prettyJson(tool.result)}
        </pre>
      )}
      {hasError && (
        <p className="mt-2 rounded-md bg-rose-50 px-2 py-1 text-[11px] text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
          {tool.error_message}
        </p>
      )}
    </div>
  );
};

export default ConsolidatedToolCallRow;

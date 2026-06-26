'use client';

import { CustomButton, CustomDrawer, CustomTooltip } from '@/components/shared';
import type { ToolExecution } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { Check, Copy } from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import {
  authFor,
  durationToneClass,
  endpointFor,
  formatDuration,
  formatStartedAt,
  prettyJson,
  statusPill,
  toolTypeChipClasses,
  toolTypeLabel,
} from './helpers';

interface ToolExecutionDetailDrawerProps {
  execution: ToolExecution | null;
  open: boolean;
  onClose: () => void;
}

function MetaCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-[13px]">{children}</dd>
    </div>
  );
}

interface SourceConfigSectionProps {
  execution: ToolExecution;
}

/** Read-only summary of the source `tools` / `mcp_servers` row this execution
 *  came from. Renders nothing if no joined fields are present (e.g. for
 *  code-defined built-ins like `end_call`). */
function SourceConfigSection({ execution }: SourceConfigSectionProps) {
  const isMcp = execution.tool_type === 'mcp';
  const description = isMcp ? execution.mcp_server_description : execution.tool_description;
  const isActive = isMcp ? execution.mcp_server_is_active : execution.tool_is_active;
  const endpoint = endpointFor(execution);
  const auth = authFor(execution);
  const method = isMcp ? null : execution.tool_method;

  const hasAny =
    description != null || endpoint != null || auth != null || method != null || isActive != null;

  if (!hasAny) return null;

  return (
    <section className="rounded-lg border border-border/60 bg-muted/30 p-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Source configuration
      </h4>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12.5px]">
        {description && (
          <div className="col-span-2">
            <dt className="text-[11px] text-muted-foreground">Description</dt>
            <dd className="mt-0.5 text-foreground">{description}</dd>
          </div>
        )}
        {endpoint && (
          <div className="col-span-2">
            <dt className="text-[11px] text-muted-foreground">Endpoint</dt>
            <dd className="mt-0.5 break-all font-mono text-[12px] text-foreground">{endpoint}</dd>
          </div>
        )}
        {method && (
          <div>
            <dt className="text-[11px] text-muted-foreground">Method</dt>
            <dd className="mt-0.5 font-mono text-foreground">{method}</dd>
          </div>
        )}
        {auth && (
          <div>
            <dt className="text-[11px] text-muted-foreground">{isMcp ? 'Transport' : 'Auth'}</dt>
            <dd className="mt-0.5 font-mono text-foreground">{auth}</dd>
          </div>
        )}
        {isActive != null && (
          <div>
            <dt className="text-[11px] text-muted-foreground">Active</dt>
            <dd
              className={cn(
                'mt-0.5 font-medium',
                isActive
                  ? 'text-emerald-700 dark:text-emerald-300'
                  : 'text-rose-700 dark:text-rose-300',
              )}
            >
              {isActive ? 'Yes' : 'No'}
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[13px] text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
      <p className="text-[11px] font-semibold uppercase tracking-wide">Error</p>
      <p className="mt-1 whitespace-pre-wrap break-words font-mono text-[12.5px]">{message}</p>
    </div>
  );
}

interface JsonBlockProps {
  label: string;
  value: unknown;
  emptyLabel: string;
}

function JsonBlock({ label, value, emptyLabel }: JsonBlockProps) {
  const text = prettyJson(value);
  const isEmpty = !text || text === '{}' || text === '[]' || text === 'null';

  const [copied, setCopied] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    },
    [],
  );

  const onCopy = useCallback(async () => {
    if (typeof window === 'undefined' || isEmpty) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can fail in insecure contexts — fail silently.
    }
  }, [isEmpty, text]);

  return (
    <section>
      <header className="mb-1.5 flex items-center justify-between">
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </h4>
        {!isEmpty && (
          <CustomTooltip content={copied ? 'Copied' : 'Copy JSON'}>
            <CustomButton
              type="text"
              size="xs"
              icon={
                copied ? (
                  <Check className="size-3 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <Copy className="size-3" />
                )
              }
              onClick={onCopy}
              aria-label={`Copy ${label.toLowerCase()}`}
            >
              {copied ? 'Copied' : 'Copy'}
            </CustomButton>
          </CustomTooltip>
        )}
      </header>
      {isEmpty ? (
        <p className="rounded-md bg-muted/40 px-3 py-2 text-[12.5px] text-muted-foreground">
          {emptyLabel}
        </p>
      ) : (
        <pre className="max-h-80 overflow-auto rounded-md border border-border/60 bg-muted/40 px-3 py-2 font-mono text-[12px] leading-relaxed text-foreground">
          {text}
        </pre>
      )}
    </section>
  );
}

/**
 * Right-side drawer that shows everything we captured for one tool invocation:
 * tool/server/status/duration/turn header, then arguments, result and (if any)
 * error message as copyable JSON blocks. Used by `ToolsMcpSection` when a row
 * in the executions table is clicked.
 */
const ToolExecutionDetailDrawer: React.FC<ToolExecutionDetailDrawerProps> = ({
  execution,
  open,
  onClose,
}) => {
  if (!execution) {
    return (
      <CustomDrawer open={open} onClose={onClose} title="Tool execution" width="w-[640px]">
        <div className="py-10 text-center text-sm text-muted-foreground">
          No execution selected.
        </div>
      </CustomDrawer>
    );
  }

  const status = statusPill(execution.status);
  const duration = formatDuration(execution.duration_ms);
  const typeClasses = toolTypeChipClasses(execution.tool_type);
  const typeLabel = toolTypeLabel(execution.tool_type);

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      width="w-[640px]"
      title={
        <div className="flex min-w-0 flex-col gap-1">
          <span className="truncate font-mono text-[14px] font-semibold text-foreground">
            {execution.tool_name}
          </span>
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                typeClasses,
              )}
            >
              {typeLabel}
            </span>
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                status.className,
              )}
            >
              {status.label}
            </span>
            {execution.mcp_server_name && (
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                {execution.mcp_server_name}
              </span>
            )}
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-5 pb-6">
        {/* Header meta — duration, turn, started at, status code. */}
        <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <MetaCell label="Duration">
            <span className={cn('font-medium', durationToneClass(duration.tone))}>
              {duration.text}
            </span>
          </MetaCell>
          <MetaCell label="Turn">
            <span className="font-medium text-foreground">
              {execution.turn_number == null ? '—' : `#${execution.turn_number}`}
            </span>
          </MetaCell>
          <MetaCell label="Started">
            <span className="font-medium text-foreground">
              {formatStartedAt(execution.started_at)}
            </span>
          </MetaCell>
          <MetaCell label="Status code">
            <span className="font-medium text-foreground">{execution.status_code ?? '—'}</span>
          </MetaCell>
        </dl>

        <SourceConfigSection execution={execution} />

        {execution.error_message && <ErrorBox message={execution.error_message} />}

        <JsonBlock label="Arguments" value={execution.arguments} emptyLabel="No arguments" />
        <JsonBlock label="Result" value={execution.result} emptyLabel="No result captured" />
      </div>
    </CustomDrawer>
  );
};

export default ToolExecutionDetailDrawer;

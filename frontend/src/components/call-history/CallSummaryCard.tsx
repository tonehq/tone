'use client';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { CustomTooltip, PhoneNumberDisplay } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { formatDuration, formatTimeOnly } from '@/utils/date';
import { ArrowRight, Clock, Phone, Radio, Server } from 'lucide-react';
import React from 'react';

import { getDisplayDurationSeconds } from './callDuration';
import { getCallStatusLabel, getCallStatusTone } from './callStatus';

interface CallSummaryCardProps {
  callLog: CallLogRow;
}

// ─── reusable chip (file-local — promote if it gets a third consumer) ────────

interface InfoChipProps {
  icon?: React.ComponentType<{ className?: string }>;
  /** Accessible label shown on hover so the chip body can stay compact. */
  tooltip: string;
  children: React.ReactNode;
}

const InfoChip: React.FC<InfoChipProps> = ({ icon: Icon, tooltip, children }) => (
  <CustomTooltip content={tooltip}>
    <span
      className={cn(
        'inline-flex cursor-default items-center gap-1.5 rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 text-xs font-medium text-foreground',
        'transition-colors hover:bg-muted/70',
      )}
    >
      {Icon && <Icon className="size-3.5 text-muted-foreground" />}
      {children}
    </span>
  </CustomTooltip>
);

/** Vertical divider used to visually group chips on the summary bar. */
const ChipDivider: React.FC = () => (
  <span aria-hidden className="mx-0.5 hidden h-4 w-px bg-border sm:block" />
);

/** Inline arrow used to pair "from → to" / "start → end" values inside one chip. */
const ChipArrow: React.FC = () => (
  <ArrowRight aria-hidden className="size-3 text-muted-foreground/70" />
);

const muted = <span className="text-muted-foreground">—</span>;

/**
 * Persistent header card rendered above every Call Detail tab
 * (Transcription / Metrics / Call Configurations).
 *
 * Renders the call's identity and key facts as a single wrap-friendly row
 * of unified pill-shaped chips. Structured into two visually-grouped halves:
 *
 *   1. State   — direction · status · duration
 *   2. Details — phones (from → to) · channel · time window (start → end)
 *
 * Paired values (phones, timestamps) collapse into a single chip with an
 * arrow separator, halving the row length and tightening the visual rhythm.
 *
 * Lives outside the scrollable `<main>` in CallDetailShell, so it stays
 * visible while the tab body scrolls — no `position: sticky` needed.
 */
const CallSummaryCard: React.FC<CallSummaryCardProps> = ({ callLog }) => {
  const startedAt = formatTimeOnly(callLog.started_at);
  const endedAt = formatTimeOnly(callLog.ended_at);
  const displayDuration = getDisplayDurationSeconds(callLog);

  const hasPhones = !!callLog.from_number || !!callLog.to_number;
  const hasTimes = !!startedAt || !!endedAt;
  const hasDetails = hasPhones || !!callLog.channel_type || hasTimes;

  const servedBy = callLog.served_by;
  const servedByTooltip = servedBy
    ? [servedBy.deployment, servedBy.node].filter(Boolean).join(' · ') || 'Served by pod'
    : '';

  return (
    <section
      aria-label="Call summary"
      className="shrink-0 border-b border-border/60 bg-muted px-5 py-3 lg:px-8"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2">
        {/* ── State group ───────────────────────────────────────────── */}
        <AgentTypeBadge agentType={callLog.agent_type} />
        <Badge className={cn('rounded-full px-2.5 py-1', getCallStatusTone(callLog.status))}>
          {getCallStatusLabel(callLog.status)}
        </Badge>
        {displayDuration != null && (
          <InfoChip icon={Clock} tooltip="Call Duration">
            {formatDuration(displayDuration)}
          </InfoChip>
        )}

        {hasDetails && <ChipDivider />}

        {/* ── Details group ─────────────────────────────────────────── */}
        {hasPhones && (
          <InfoChip icon={Phone} tooltip="From → To Number">
            {/* `[&_span]:text-xs` shrinks PhoneNumberDisplay's inner number
                text from its default `text-sm` to match the chip — scoped
                locally so other consumers of PhoneNumberDisplay are unaffected. */}
            {callLog.from_number ? (
              <PhoneNumberDisplay
                phoneNumber={callLog.from_number}
                flagSize="sm"
                className="[&_span]:text-xs"
              />
            ) : (
              muted
            )}
            <ChipArrow />
            {callLog.to_number ? (
              <PhoneNumberDisplay
                phoneNumber={callLog.to_number}
                flagSize="sm"
                className="[&_span]:text-xs"
              />
            ) : (
              muted
            )}
          </InfoChip>
        )}

        {callLog.channel_type && (
          <InfoChip icon={Radio} tooltip="Channel Type">
            {callLog.channel_type}
          </InfoChip>
        )}

        {hasTimes && (
          <InfoChip icon={Clock} tooltip="Call Time (Start → End)">
            {startedAt ?? muted}
            <ChipArrow />
            {endedAt ?? muted}
          </InfoChip>
        )}

        {servedBy?.pod && (
          <InfoChip icon={Server} tooltip={servedByTooltip}>
            {servedBy.pod}
          </InfoChip>
        )}
      </div>
    </section>
  );
};

export default CallSummaryCard;

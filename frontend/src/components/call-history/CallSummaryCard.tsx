'use client';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { PhoneNumberDisplay } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { formatDuration, formatTimestamp } from '@/utils/date';
import { Clock, Phone, PhoneOff, Radio } from 'lucide-react';
import React from 'react';

import { getCallStatusLabel, getCallStatusTone } from './callStatus';

interface CallSummaryCardProps {
  callLog: CallLogRow;
}

interface DetailFieldProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  className?: string;
  children: React.ReactNode;
}

const DetailField: React.FC<DetailFieldProps> = ({ icon: Icon, label, className, children }) => (
  <div className={cn('flex items-start gap-2', className)}>
    <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      {children}
    </div>
  </div>
);

/**
 * Persistent header card rendered above every Call Detail tab
 * (Transcription / Metrics / Call Configurations).
 *
 * It is placed OUTSIDE the scrollable `<main>` in CallDetailShell, so it
 * stays visible while the tab body scrolls — no `position: sticky` needed,
 * which keeps the markup simple and avoids stacking-context surprises.
 */
const CallSummaryCard: React.FC<CallSummaryCardProps> = ({ callLog }) => (
  <section
    aria-label="Call summary"
    className="shrink-0 border-b border-border/60 bg-background px-5 py-4 lg:px-8"
  >
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      {/* Status badges */}
      <div className="flex flex-wrap items-center gap-2">
        <AgentTypeBadge agentType={callLog.agent_type} />
        <Badge className={cn('px-2.5 py-1', getCallStatusTone(callLog.status))}>
          {getCallStatusLabel(callLog.status)}
        </Badge>
        {callLog.duration_seconds != null && (
          <Badge variant="outline" className="px-2.5 py-1">
            <Clock className="size-3.5" />
            {formatDuration(callLog.duration_seconds)}
          </Badge>
        )}
      </div>

      <Separator />

      {/* Call Details */}
      <div>
        <h3 className="mb-3 text-sm font-medium text-foreground">Call Details</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <DetailField icon={Phone} label="From Number">
            {callLog.from_number ? (
              <PhoneNumberDisplay phoneNumber={callLog.from_number} flagSize="sm" />
            ) : (
              <p className="text-sm">-</p>
            )}
          </DetailField>
          <DetailField icon={PhoneOff} label="To Number">
            {callLog.to_number ? (
              <PhoneNumberDisplay phoneNumber={callLog.to_number} flagSize="sm" />
            ) : (
              <p className="text-sm">-</p>
            )}
          </DetailField>
          <DetailField icon={Radio} label="Channel Type">
            <p className="text-sm">{callLog.channel_type || '-'}</p>
          </DetailField>
          <DetailField icon={Clock} label="Call Start Time">
            <p className="text-sm">{formatTimestamp(callLog.started_at)}</p>
          </DetailField>
          <DetailField icon={Clock} label="Call End Time" className="sm:col-span-2">
            <p className="text-sm">{formatTimestamp(callLog.ended_at)}</p>
          </DetailField>
        </div>
      </div>
    </div>
  </section>
);

export default CallSummaryCard;

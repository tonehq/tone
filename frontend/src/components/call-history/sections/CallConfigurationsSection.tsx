'use client';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { AppLoader, PhoneNumberDisplay } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { formatDuration, formatTimestamp } from '@/utils/date';
import { BrainCircuit, Clock, Mic, Phone, PhoneOff, Radio, Volume2 } from 'lucide-react';
import React from 'react';

import { getCallStatusLabel, getCallStatusTone } from '../callStatus';
import { useCallConfiguration } from './useCallConfiguration';

interface CallConfigurationsSectionProps {
  callLog: CallLogRow;
}

// ─── small building blocks (file-local, used only here) ──────────────────────

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

const dash = <span className="text-muted-foreground/60">—</span>;

interface KeyValueProps {
  label: string;
  value: string | null;
}

const KeyValue: React.FC<KeyValueProps> = ({ label, value }) => (
  <div>
    <p className="text-[11px] uppercase tracking-wider text-muted-foreground/70">{label}</p>
    <div className="mt-0.5">
      {value ? <span className="text-sm font-medium text-foreground">{value}</span> : dash}
    </div>
  </div>
);

interface PipelineCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  /** Ordered list of label/value rows displayed in a 1- or 2-column grid. */
  rows: Array<{ label: string; value: string | null }>;
}

const PipelineCard: React.FC<PipelineCardProps> = ({ icon: Icon, title, rows }) => (
  <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/20 p-4">
    <div className="flex items-center gap-2">
      <span className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-inset ring-primary/15">
        <Icon className="size-3.5" />
      </span>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
    </div>
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {rows.map((row) => (
        <KeyValue key={row.label} label={row.label} value={row.value} />
      ))}
    </div>
  </div>
);

// ─── section ──────────────────────────────────────────────────────────────────

const CallConfigurationsSection: React.FC<CallConfigurationsSectionProps> = ({ callLog }) => {
  const { data: pipeline, loading: pipelineLoading } = useCallConfiguration({
    agentId: callLog.agent_id,
    metrics: callLog.metrics,
  });

  // Hold the entire tab on the project's shared loader until the pipeline is
  // ready, so the page doesn't paint Call Details first and then shift when
  // Pipeline lands.
  if (pipelineLoading && !pipeline) {
    return <AppLoader className="h-full" />;
  }

  return (
    <div className="flex flex-col">
      {/* Header badges */}
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

      <Separator className="my-4" />

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

      <Separator className="my-6" />

      {/* Pipeline */}
      <div>
        <h3 className="mb-1 text-sm font-medium text-foreground">Pipeline</h3>
        <p className="mb-3 text-xs text-muted-foreground">
          Reflects the agent&apos;s current configuration. Model names come from this call&apos;s
          metrics when available.
        </p>

        {!pipeline ? (
          <p className="text-sm text-muted-foreground">
            Pipeline configuration is not available for this call.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            <PipelineCard
              icon={BrainCircuit}
              title="LLM (Reasoning)"
              rows={[
                { label: 'Provider', value: pipeline.llm.provider },
                { label: 'Model', value: pipeline.llm.model },
              ]}
            />
            <PipelineCard
              icon={Mic}
              title="STT (Speech-to-Text)"
              rows={[
                { label: 'Provider', value: pipeline.stt.provider },
                { label: 'Model', value: pipeline.stt.model },
              ]}
            />
            <PipelineCard
              icon={Volume2}
              title="TTS (Text-to-Speech)"
              rows={[
                { label: 'Provider', value: pipeline.tts.provider },
                { label: 'Model', value: pipeline.tts.model },
                { label: 'Language', value: pipeline.language },
                { label: 'Voice', value: pipeline.voice },
              ]}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default CallConfigurationsSection;

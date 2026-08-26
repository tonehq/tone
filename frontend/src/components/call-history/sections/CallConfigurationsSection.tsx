'use client';

import { IconChip } from '@/components/shared';
import type { CallLogRow } from '@/types/callLog';
import { BrainCircuit, Mic, Volume2 } from 'lucide-react';
import React from 'react';

import { useCallConfiguration } from './useCallConfiguration';

interface CallConfigurationsSectionProps {
  callLog: CallLogRow;
}

// ─── small building blocks (file-local) ──────────────────────────────────────

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
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  /** Ordered list of label/value rows displayed in a 1- or 2-column grid. */
  rows: Array<{ label: string; value: string | null }>;
}

const PipelineCard: React.FC<PipelineCardProps> = ({ icon: Icon, title, rows }) => (
  <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/20 p-4">
    <div className="flex items-center gap-2">
      <IconChip icon={<Icon strokeWidth={1.75} />} tone="primary" size="sm" />
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
  // Derived synchronously from the call's immutable pipeline snapshot — no
  // fetch, so there's no loading state to hold the tab on.
  const { data: pipeline } = useCallConfiguration({
    pipelineConfig: callLog.pipeline_config,
    metrics: callLog.metrics,
  });

  return (
    <div className="flex flex-col">
      <h3 className="mb-1 text-sm font-medium text-foreground">Pipeline</h3>
      <p className="mb-3 text-xs text-muted-foreground">
        Reflects the configuration used for this call. Model names come from this call&apos;s
        configuration, falling back to its metrics.
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
  );
};

export default CallConfigurationsSection;

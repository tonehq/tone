'use client';

import type { CallMetrics } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { BrainCircuit, Gauge, MessageSquare, Mic } from 'lucide-react';
import React, { useMemo } from 'react';

import { LLMUsageSection } from './LLMUsageSection';
import { MetricsCategory } from './MetricsCategory';
import { ProcessingTimesSection } from './ProcessingTimesSection';
import { StatCard } from './StatCard';
import { TTSUsageSection } from './TTSUsageSection';
import { TurnLatencySection } from './TurnLatencySection';

interface MetricsContentProps {
  metrics: CallMetrics;
  className?: string;
}

const MetricsContent: React.FC<MetricsContentProps> = ({ metrics, className }) => {
  // Defensive shims — the type declares each as a non-null array, but legacy
  // backend rows / partial ingestion can deliver `null`. Coerce once at the
  // top so every downstream `.reduce`/`.map`/`.filter` is safe.
  const userBotLatency = Array.isArray(metrics.user_bot_latency) ? metrics.user_bot_latency : [];
  const llmUsage = Array.isArray(metrics.llm_usage) ? metrics.llm_usage : [];
  const ttsUsage = Array.isArray(metrics.tts_usage) ? metrics.tts_usage : [];
  const turnsList = Array.isArray(metrics.turns) ? metrics.turns : [];
  const processingList = Array.isArray(metrics.processing) ? metrics.processing : [];
  const turnMetrics = Array.isArray(metrics.turn_metrics) ? metrics.turn_metrics : [];

  const overview = useMemo(() => {
    const avgLatency =
      userBotLatency.length > 0
        ? userBotLatency.reduce((sum, l) => sum + l.latency, 0) / userBotLatency.length
        : null;
    const totalTokens = llmUsage.reduce((sum, u) => sum + u.total_tokens, 0);
    const totalChars = ttsUsage.reduce((sum, u) => sum + u.characters, 0);
    // Count real user→bot exchanges when per-turn data is available — drops
    // the greeting (bot spoke first), abandoned turns, and pre/inter-turn
    // buckets. Falls back to the raw pipecat turn count for legacy calls
    // recorded before `turn_metrics` was being collected.
    const totalTurns =
      turnMetrics.length > 0
        ? turnMetrics.filter((t) => t.end_to_end != null).length
        : turnsList.length;
    return { avgLatency, totalTokens, totalChars, totalTurns };
  }, [userBotLatency, llmUsage, ttsUsage, turnsList, turnMetrics]);

  const hasProcessing = processingList.some((p) => p.model && p.value > 0);
  const hasTurnMetrics = turnMetrics.length > 0;
  const hasLatency = hasTurnMetrics || hasProcessing;
  const hasUsage = llmUsage.length > 0 || ttsUsage.length > 0;
  const llmModels = [...new Set(llmUsage.map((u) => u.model))].join(', ');

  return (
    <div className={cn('flex flex-col gap-8', className)}>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={Gauge}
          label="Avg Latency"
          value={overview.avgLatency != null ? `${overview.avgLatency.toFixed(1)}s` : '-'}
          sub="User to bot"
          color="bg-violet-500"
        />
        <StatCard
          icon={MessageSquare}
          label="Turns"
          value={String(overview.totalTurns)}
          color="bg-blue-500"
        />
        <StatCard
          icon={BrainCircuit}
          label="LLM Tokens"
          value={overview.totalTokens.toLocaleString()}
          sub={llmUsage.length > 0 ? llmModels : undefined}
          color="bg-emerald-500"
        />
        <StatCard
          icon={Mic}
          label="TTS Characters"
          value={overview.totalChars.toLocaleString()}
          sub={ttsUsage.length > 0 ? ttsUsage[0].model : undefined}
          color="bg-amber-500"
        />
      </div>

      {hasLatency && (
        <MetricsCategory title="Latency">
          {hasTurnMetrics && <TurnLatencySection turns={turnMetrics} />}
          {hasProcessing && <ProcessingTimesSection processing={processingList} />}
        </MetricsCategory>
      )}

      {hasUsage && (
        <MetricsCategory title="Usage">
          {llmUsage.length > 0 && (
            <LLMUsageSection llmUsage={llmUsage} totalTokens={overview.totalTokens} />
          )}
          {ttsUsage.length > 0 && (
            <TTSUsageSection ttsUsage={ttsUsage} totalChars={overview.totalChars} />
          )}
        </MetricsCategory>
      )}
    </div>
  );
};

export default MetricsContent;

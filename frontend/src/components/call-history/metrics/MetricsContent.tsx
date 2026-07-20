'use client';

import { CustomButton } from '@/components/shared';
import type { CallMetrics, ToolExecution } from '@/types/callLog';
import { cn } from '@/utils/cn';
import {
  AudioLines,
  BrainCircuit,
  ChevronsDownUp,
  ChevronsUpDown,
  Gauge,
  MessageSquare,
  Mic,
} from 'lucide-react';
import React, { useMemo } from 'react';

import { EndToEndLatencyPercentileSection } from './EndToEndLatencyPercentileSection';
import { LLMUsageSection } from './LLMUsageSection';
import { MetricsCategory } from './MetricsCategory';
import { MetricsCollapseProvider, useMetricsCollapse } from './MetricsCollapseContext';
import { PerTurnCallsSection } from './PerTurnCallsSection';
import { ProcessingTimesSection } from './ProcessingTimesSection';
import { StatCard } from './StatCard';
import { STTUsageSection } from './STTUsageSection';
import { TTSUsageSection } from './TTSUsageSection';
import { TurnLatencySection } from './TurnLatencySection';
import { UserBotLatencySection } from './UserBotLatencySection';
import { formatAudioMs, formatMs } from './utils';

function CollapseToolbar() {
  const { expandAll, collapseAll } = useMetricsCollapse();
  return (
    <div className="flex items-center justify-end gap-2">
      <CustomButton
        type="text"
        size="sm"
        icon={<ChevronsUpDown className="size-4" />}
        onClick={expandAll}
      >
        Expand all
      </CustomButton>
      <CustomButton
        type="text"
        size="sm"
        icon={<ChevronsDownUp className="size-4" />}
        onClick={collapseAll}
      >
        Collapse all
      </CustomButton>
    </div>
  );
}

interface MetricsContentProps {
  metrics: CallMetrics;
  /** Tool executions for this call — sourced from `/tool-executions`. Used by
   *  the End-to-End per-Turn table to show the count of executed (success/error)
   *  tool calls per turn. */
  toolExecutions?: ToolExecution[];
  className?: string;
}

const MetricsContent: React.FC<MetricsContentProps> = ({ metrics, toolExecutions, className }) => {
  // Defensive shims — the type declares each as a non-null array, but legacy
  // backend rows / partial ingestion can deliver `null`. Coerce once at the
  // top so every downstream `.reduce`/`.map`/`.filter` is safe.
  const userBotLatency = Array.isArray(metrics.user_bot_latency) ? metrics.user_bot_latency : [];
  const llmUsage = Array.isArray(metrics.llm_usage) ? metrics.llm_usage : [];
  const ttsUsage = Array.isArray(metrics.tts_usage) ? metrics.tts_usage : [];
  const sttUsage = Array.isArray(metrics.stt_usage) ? metrics.stt_usage : [];
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
    const totalSttAudioMs = sttUsage.reduce((sum, u) => sum + u.audio_ms, 0);
    // Count real user→bot exchanges when per-turn data is available — drops
    // the greeting (bot spoke first), abandoned turns, and pre/inter-turn
    // buckets. Falls back to the raw pipecat turn count for legacy calls
    // recorded before `turn_metrics` was being collected.
    const totalTurns =
      turnMetrics.length > 0
        ? turnMetrics.filter((t) => t.end_to_end != null).length
        : turnsList.length;
    return { avgLatency, totalTokens, totalChars, totalSttAudioMs, totalTurns };
  }, [userBotLatency, llmUsage, ttsUsage, sttUsage, turnsList, turnMetrics]);

  const hasProcessing = processingList.some((p) => p.model && p.value > 0);
  const hasTurnMetrics = turnMetrics.length > 0;
  const hasLatency = hasTurnMetrics || hasProcessing || userBotLatency.length > 0;
  const hasUsage = llmUsage.length > 0 || ttsUsage.length > 0 || sttUsage.length > 0;
  const llmModels = [...new Set(llmUsage.map((u) => u.model))].join(', ');

  const showCollapseToolbar = hasLatency || hasUsage;

  return (
    <MetricsCollapseProvider>
      <div className={cn('flex flex-col gap-8', className)}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard
            icon={Gauge}
            label="Avg Latency"
            value={overview.avgLatency != null ? formatMs(overview.avgLatency) : '-'}
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
          <StatCard
            icon={AudioLines}
            label="STT Audio"
            value={formatAudioMs(overview.totalSttAudioMs)}
            sub={sttUsage.length > 0 ? (sttUsage[0].model ?? undefined) : undefined}
            color="bg-cyan-500"
          />
        </div>

        {showCollapseToolbar && <CollapseToolbar />}

        {hasLatency && (
          <MetricsCategory title="Latency">
            {hasTurnMetrics && (
              <TurnLatencySection turns={turnMetrics} toolExecutions={toolExecutions} />
            )}
            <UserBotLatencySection latencies={userBotLatency.map((l) => l.latency)} />
            <EndToEndLatencyPercentileSection latencies={userBotLatency.map((l) => l.latency)} />
            {hasTurnMetrics && <PerTurnCallsSection turns={turnMetrics} />}
            {hasProcessing && <ProcessingTimesSection processing={processingList} />}
          </MetricsCategory>
        )}

        {hasUsage && (
          <MetricsCategory title="Usage">
            {llmUsage.length > 0 && (
              <LLMUsageSection
                llmUsage={llmUsage}
                totalTokens={overview.totalTokens}
                turns={turnMetrics}
              />
            )}
            {ttsUsage.length > 0 && (
              <TTSUsageSection
                ttsUsage={ttsUsage}
                totalChars={overview.totalChars}
                turns={turnMetrics}
              />
            )}
            {sttUsage.length > 0 && (
              <STTUsageSection
                sttUsage={sttUsage}
                totalAudioMs={overview.totalSttAudioMs}
                turns={turnMetrics}
              />
            )}
          </MetricsCategory>
        )}
      </div>
    </MetricsCollapseProvider>
  );
};

export default MetricsContent;

'use client';

import type { CallMetrics } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { BrainCircuit, Gauge, MessageSquare, Mic } from 'lucide-react';
import React, { useMemo } from 'react';

import { EndToEndLatencySection } from './EndToEndLatencySection';
import { LLMUsageSection } from './LLMUsageSection';
import { MetricsCategory } from './MetricsCategory';
import { ProcessingTimesSection } from './ProcessingTimesSection';
import { StatCard } from './StatCard';
import { TTFBSection } from './TTFBSection';
import { TTSUsageSection } from './TTSUsageSection';
import { extractProcessorName } from './utils';

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
  const ttfbList = Array.isArray(metrics.ttfb) ? metrics.ttfb : [];
  const processingList = Array.isArray(metrics.processing) ? metrics.processing : [];

  const overview = useMemo(() => {
    const avgLatency =
      userBotLatency.length > 0
        ? userBotLatency.reduce((sum, l) => sum + l.latency, 0) / userBotLatency.length
        : null;
    const totalTokens = llmUsage.reduce((sum, u) => sum + u.total_tokens, 0);
    const totalChars = ttsUsage.reduce((sum, u) => sum + u.characters, 0);
    const totalTurns = turnsList.length;
    return { avgLatency, totalTokens, totalChars, totalTurns };
  }, [userBotLatency, llmUsage, ttsUsage, turnsList]);

  const ttfbByProcessor = useMemo(() => {
    // Keep entries even when `model` is null — some custom STT services
    // (e.g. NvidiaWebSocketService in the tonehq/pipecat fork) emit TTFB
    // without setting `set_model_name(...)`. Filtering on `e.model` would
    // silently drop the entire STT card. The processor name is enough to
    // identify the source; the model label simply renders blank when absent.
    const entries = ttfbList.filter((e) => e.value > 0);
    return entries.reduce(
      (acc, e) => {
        const name = extractProcessorName(e.processor);
        if (!acc[name]) acc[name] = [];
        acc[name].push(e);
        return acc;
      },
      {} as Record<string, typeof entries>,
    );
  }, [ttfbList]);

  const hasTtfb = Object.keys(ttfbByProcessor).length > 0;
  const hasProcessing = processingList.some((p) => p.model && p.value > 0);
  const hasLatency = hasTtfb || userBotLatency.length > 0 || hasProcessing;
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
          {hasTtfb && <TTFBSection ttfbByProcessor={ttfbByProcessor} />}
          {userBotLatency.length > 0 && <EndToEndLatencySection latencies={userBotLatency} />}
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

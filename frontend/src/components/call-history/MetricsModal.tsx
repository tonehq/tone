'use client';

import { CustomModal } from '@/components/shared';
import type { CallMetrics } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { Activity, BrainCircuit, Gauge, MessageSquare, Mic, Timer, Zap } from 'lucide-react';
import React, { useMemo } from 'react';

import { BarChart } from './metrics/BarChart';
import { LLMUsageSection } from './metrics/LLMUsageSection';
import { ProcessingTimesSection } from './metrics/ProcessingTimesSection';
import { SectionHeader } from './metrics/SectionHeader';
import { StatCard } from './metrics/StatCard';
import { TTSUsageSection } from './metrics/TTSUsageSection';
import { BAR_CHART_MAX_HEIGHT, extractProcessorName, formatMs } from './metrics/utils';

interface MetricsModalProps {
  open: boolean;
  onClose: () => void;
  metrics: CallMetrics | null;
  agentName: string;
}

const MetricsModal: React.FC<MetricsModalProps> = ({ open, onClose, metrics, agentName }) => {
  const summary = useMemo(() => {
    if (!metrics) return null;

    const ttfbEntries = metrics.ttfb.filter((e) => e.model && e.value > 0);
    const avgLatency =
      metrics.user_bot_latency.length > 0
        ? metrics.user_bot_latency.reduce((sum, l) => sum + l.latency, 0) /
          metrics.user_bot_latency.length
        : null;

    const totalTokens = metrics.llm_usage.reduce((sum, u) => sum + u.total_tokens, 0);
    const totalChars = metrics.tts_usage.reduce((sum, u) => sum + u.characters, 0);
    const totalTurns = metrics.turns.length;

    const ttfbByProcessor = ttfbEntries.reduce(
      (acc, e) => {
        const name = extractProcessorName(e.processor);
        if (!acc[name]) acc[name] = [];
        acc[name].push(e);
        return acc;
      },
      {} as Record<string, typeof ttfbEntries>,
    );

    return { avgLatency, totalTokens, totalChars, totalTurns, ttfbByProcessor, ttfbEntries };
  }, [metrics]);

  if (!metrics || !summary) return null;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={`Metrics${agentName ? ` — ${agentName}` : ''}`}
      width="md:max-w-2xl"
      hideFooter
      contentClassName="max-h-[70vh] overflow-y-auto pr-0"
    >
      <div className="flex flex-col gap-5 pr-6">
        {/* Overview Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard
            icon={Gauge}
            label="Avg Latency"
            value={summary.avgLatency != null ? `${summary.avgLatency.toFixed(1)}s` : '-'}
            sub="User to bot"
            color="bg-violet-500"
          />
          <StatCard
            icon={MessageSquare}
            label="Turns"
            value={String(summary.totalTurns)}
            sub={
              summary.totalTurns > 0
                ? `${metrics.turns.filter((t) => t.status === 'completed').length} completed`
                : undefined
            }
            color="bg-blue-500"
          />
          <StatCard
            icon={BrainCircuit}
            label="LLM Tokens"
            value={summary.totalTokens.toLocaleString()}
            sub={
              metrics.llm_usage.length > 0
                ? [...new Set(metrics.llm_usage.map((u) => u.model))].join(', ')
                : undefined
            }
            color="bg-emerald-500"
          />
          <StatCard
            icon={Mic}
            label="TTS Characters"
            value={summary.totalChars.toLocaleString()}
            sub={metrics.tts_usage.length > 0 ? metrics.tts_usage[0].model : undefined}
            color="bg-amber-500"
          />
        </div>

        {/* TTFB Breakdown */}
        {summary.ttfbEntries.length > 0 && (
          <div className="space-y-3">
            <SectionHeader icon={Zap} title="Time to First Byte (TTFB)" />
            <div className="space-y-2">
              {Object.entries(summary.ttfbByProcessor).map(([processor, entries]) => {
                const avg = entries.reduce((s, e) => s + e.value, 0) / entries.length;
                const max = Math.max(...entries.map((e) => e.value));
                const model = entries.find((e) => e.model)?.model;
                return (
                  <div key={processor} className="rounded-lg border border-border p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium text-foreground">{processor}</span>
                        {model && (
                          <span className="ml-2 text-xs text-muted-foreground">{model}</span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entries.length} sample{entries.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="flex gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Avg</p>
                        <p className="text-sm font-semibold text-foreground">{formatMs(avg)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Max</p>
                        <p className="text-sm font-semibold text-foreground">{formatMs(max)}</p>
                      </div>
                    </div>
                    <BarChart
                      values={entries.map((e) => e.value)}
                      maxValue={max}
                      maxHeight={BAR_CHART_MAX_HEIGHT}
                      color="bg-primary/60 hover:bg-primary"
                      getTooltip={(v) => formatMs(v)}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Conversation Turns */}
        {metrics.turns.length > 0 && (
          <div className="space-y-3">
            <SectionHeader icon={Timer} title="Conversation Turns" />
            <div className="overflow-hidden rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50">
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                      Turn
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">
                      Duration
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.turns.map((turn) => (
                    <tr key={turn.turn} className="border-b border-border last:border-0">
                      <td className="px-3 py-2 font-medium text-foreground">#{turn.turn}</td>
                      <td className="px-3 py-2">
                        <span
                          className={cn(
                            'inline-flex items-center capitalize rounded-full px-2 py-0.5 text-xs font-medium',
                            turn.status === 'completed'
                              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                              : 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
                          )}
                        >
                          {turn.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-muted-foreground">
                        {turn.duration.toFixed(3)}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* LLM Usage */}
        {metrics.llm_usage.length > 0 && (
          <LLMUsageSection llmUsage={metrics.llm_usage} totalTokens={summary.totalTokens} />
        )}

        {/* TTS Usage */}
        {metrics.tts_usage.length > 0 && (
          <TTSUsageSection ttsUsage={metrics.tts_usage} totalChars={summary.totalChars} />
        )}

        {/* User-Bot Latency */}
        {metrics.user_bot_latency.length > 0 && (
          <div className="space-y-3">
            <SectionHeader icon={Activity} title="End-to-End Latency" />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {metrics.user_bot_latency.map((l, i) => (
                <div key={i} className="rounded-lg border border-border p-3 text-center">
                  <p className="text-xs text-muted-foreground">
                    {metrics.user_bot_latency.length > 1 ? `Measurement ${i + 1}` : 'Latency'}
                  </p>
                  <p
                    className={cn(
                      'mt-1 text-lg font-bold',
                      l.latency < 3
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : l.latency < 7
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-red-600 dark:text-red-400',
                    )}
                  >
                    {l.latency.toFixed(3)}s
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Times */}
        <ProcessingTimesSection processing={metrics.processing} />
      </div>
    </CustomModal>
  );
};

export default MetricsModal;

import type { CallMetricsProcessing } from '@/types/callLog';

export const BAR_CHART_MAX_HEIGHT = 50;

export interface ProcessorGroup {
  model: string;
  entries: number[];
}

export function formatMs(seconds: number): string {
  if (seconds < 0.001) return '< 1ms';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  return `${seconds.toFixed(2)}s`;
}

export function extractProcessorName(processor: string): string {
  return processor.replace(/#\d+$/, '');
}

export function groupByProcessor(entries: CallMetricsProcessing[]): Record<string, ProcessorGroup> {
  return entries.reduce(
    (acc, p) => {
      const key = extractProcessorName(p.processor);
      if (!acc[key]) acc[key] = { model: p.model!, entries: [] };
      acc[key].entries.push(p.value);
      return acc;
    },
    {} as Record<string, ProcessorGroup>,
  );
}

import type { CallMetricsProcessing } from '@/types/callLog';
import { Clock } from 'lucide-react';

import { SectionHeader } from './SectionHeader';
import { formatMs, groupByProcessor } from './utils';

interface ProcessingTimesSectionProps {
  processing: CallMetricsProcessing[];
}

export function ProcessingTimesSection({ processing }: ProcessingTimesSectionProps) {
  const significant = processing.filter((p) => p.model && p.value > 0);
  if (significant.length === 0) return null;

  const grouped = groupByProcessor(significant);

  return (
    <div className="space-y-3">
      <SectionHeader icon={Clock} title="Processing Times" />
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                Processor
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">
                Model
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">
                Avg
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">
                Total
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">
                Calls
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(grouped).map(([processor, data]) => {
              const total = data.entries.reduce((s, v) => s + v, 0);
              const avg = total / data.entries.length;
              return (
                <tr key={processor} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 font-medium text-foreground">{processor}</td>
                  <td className="px-3 py-2 text-muted-foreground">{data.model}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">{formatMs(avg)}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">{formatMs(total)}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">
                    {data.entries.length}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

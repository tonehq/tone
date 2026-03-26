import { cn } from '@/utils/cn';

interface BarChartProps {
  values: number[];
  maxValue: number;
  maxHeight: number;
  color: string;
  getTooltip: (value: number, index: number) => string;
}

export function BarChart({ values, maxValue, maxHeight, color, getTooltip }: BarChartProps) {
  return (
    <div className="flex items-end gap-px">
      {values.map((v, i) => {
        const height = maxValue > 0 ? Math.max((v / maxValue) * maxHeight, 2) : 2;
        return (
          <div
            key={i}
            className={cn('flex-1 rounded-t transition-all', color)}
            style={{ height: `${height}px` }}
            title={getTooltip(v, i)}
          />
        );
      })}
    </div>
  );
}

'use client';

import { cn } from '@/utils/cn';

const BAR_COUNT = 56;

const BARS = Array.from({ length: BAR_COUNT }, (_, i) => {
  const t = i / (BAR_COUNT - 1);
  const envelope =
    0.3 +
    0.42 * Math.exp(-Math.pow((t - 0.26) * 4.4, 2)) +
    0.58 * Math.exp(-Math.pow((t - 0.68) * 3.2, 2));
  const detail = 0.55 + 0.45 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.9));
  return Math.max(0.1, Math.min(1, envelope * detail));
});

export interface BrandWaveformProps {
  className?: string;
  barClassName?: string;
}

export default function BrandWaveform({ className, barClassName }: BrandWaveformProps) {
  return (
    <div aria-hidden className={cn('flex items-end gap-[3px]', className)}>
      {BARS.map((height, i) => (
        <span
          key={i}
          className={cn('flex-1 rounded-full bg-white', barClassName)}
          style={{ height: `${height * 100}%`, opacity: 0.2 + height * 0.55 }}
        />
      ))}
    </div>
  );
}

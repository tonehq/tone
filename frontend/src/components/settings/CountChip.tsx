import { cn } from '@/utils/cn';

interface CountChipProps {
  value: number | null;
  dim?: boolean;
}

/** Small rounded count pill next to the integrations tab labels/headers. */
export default function CountChip({ value, dim = false }: CountChipProps) {
  if (value === null) return null;
  return (
    <span
      className={cn(
        'inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1.5 text-[10px] font-semibold tabular-nums',
        dim ? 'bg-foreground/5 text-foreground/60' : 'bg-foreground/10 text-foreground/80',
      )}
    >
      {value}
    </span>
  );
}

import { cn } from '@/utils/cn';

export default function StatusPill({
  active,
  compact = false,
}: {
  active: boolean;
  compact?: boolean;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full text-[10px] font-medium',
        compact ? 'px-2 py-0.5' : 'px-2 py-0.5',
        active
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
          : 'bg-muted text-muted-foreground',
      )}
    >
      <span
        className={cn(
          'size-1.5 rounded-full',
          active ? 'animate-pulse bg-emerald-500' : 'bg-muted-foreground/50',
        )}
      />
      {active ? 'Active' : 'Paused'}
    </span>
  );
}

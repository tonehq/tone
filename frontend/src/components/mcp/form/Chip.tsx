import type { ReactNode } from 'react';

export default function Chip({ icon, label }: { icon?: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 px-2 py-0.5 text-[11px] font-medium text-foreground backdrop-blur dark:bg-background/40">
      {icon && <span className="text-muted-foreground">{icon}</span>}
      {label}
    </span>
  );
}

'use client';

import { cn } from '@/lib/utils';

// Shared initials avatar used by the main app sidebar and the settings rail.
export function AvatarBadge({
  children,
  size = 'md',
}: {
  children: React.ReactNode;
  size?: 'sm' | 'md';
}) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary',
        size === 'md' ? 'h-8 w-8' : 'h-7 w-7',
      )}
    >
      {children}
    </div>
  );
}

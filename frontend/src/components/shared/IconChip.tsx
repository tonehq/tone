'use client';

import type React from 'react';

import { cn } from '@/utils/cn';

export type IconChipTone =
  | 'primary'
  | 'indigo'
  | 'amber'
  | 'emerald'
  | 'violet'
  | 'sky'
  | 'rose'
  | 'slate'
  | 'muted';

export type IconChipSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export const ICON_CHIP_TONES: Record<IconChipTone, string> = {
  primary: 'bg-primary/10 text-primary ring-primary/20',
  indigo: 'bg-primary/10 text-primary ring-primary/20',
  amber:
    'bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300 dark:ring-amber-400/25',
  emerald:
    'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300 dark:ring-emerald-400/25',
  violet: 'bg-teal-500/10 text-teal-700 ring-teal-500/20 dark:text-teal-300 dark:ring-teal-400/25',
  sky: 'bg-sky-500/10 text-sky-700 ring-sky-500/20 dark:text-sky-300 dark:ring-sky-400/25',
  rose: 'bg-rose-500/10 text-rose-700 ring-rose-500/20 dark:text-rose-300 dark:ring-rose-400/25',
  slate:
    'bg-slate-500/10 text-slate-700 ring-slate-500/20 dark:text-slate-300 dark:ring-slate-400/25',
  muted: 'bg-muted text-muted-foreground ring-border',
};

const SIZES: Record<IconChipSize, string> = {
  sm: 'size-7 rounded-md [&_svg]:size-3.5',
  md: 'size-9 rounded-md [&_svg]:size-4',
  lg: 'size-11 rounded-lg [&_svg]:size-[1.15rem]',
  xl: 'size-14 rounded-lg [&_svg]:size-6',
  '2xl': 'size-16 rounded-xl [&_svg]:size-7',
};

export interface IconChipProps {
  icon?: React.ReactNode;
  tone?: IconChipTone;
  size?: IconChipSize;
  interactive?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export default function IconChip({
  icon,
  tone = 'muted',
  size = 'md',
  interactive = false,
  className,
  children,
}: IconChipProps) {
  return (
    <span
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center ring-1 ring-inset',
        'transition-colors duration-150',
        SIZES[size],
        ICON_CHIP_TONES[tone],
        interactive && 'group-hover:ring-current/40',
        className,
      )}
    >
      <span className="flex items-center justify-center">{icon ?? children}</span>
    </span>
  );
}

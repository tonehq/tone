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
  primary:
    'from-primary/25 via-primary/10 text-primary ring-primary/25 dark:from-primary/35 dark:via-primary/15 dark:ring-primary/35',
  indigo:
    'from-indigo-500/30 via-indigo-500/10 text-indigo-700 ring-indigo-500/25 dark:from-indigo-400/30 dark:via-indigo-400/10 dark:text-indigo-200 dark:ring-indigo-400/30',
  amber:
    'from-amber-500/30 via-amber-500/10 text-amber-700 ring-amber-500/25 dark:from-amber-400/30 dark:via-amber-400/10 dark:text-amber-200 dark:ring-amber-400/30',
  emerald:
    'from-emerald-500/30 via-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:from-emerald-400/30 dark:via-emerald-400/10 dark:text-emerald-200 dark:ring-emerald-400/30',
  violet:
    'from-violet-500/30 via-violet-500/10 text-violet-700 ring-violet-500/25 dark:from-violet-400/30 dark:via-violet-400/10 dark:text-violet-200 dark:ring-violet-400/30',
  sky: 'from-sky-500/30 via-sky-500/10 text-sky-700 ring-sky-500/25 dark:from-sky-400/30 dark:via-sky-400/10 dark:text-sky-200 dark:ring-sky-400/30',
  rose: 'from-rose-500/30 via-rose-500/10 text-rose-700 ring-rose-500/25 dark:from-rose-400/30 dark:via-rose-400/10 dark:text-rose-200 dark:ring-rose-400/30',
  slate:
    'from-slate-500/25 via-slate-500/10 text-slate-700 ring-slate-500/25 dark:from-slate-400/25 dark:via-slate-400/10 dark:text-slate-200 dark:ring-slate-400/25',
  muted: 'from-muted via-muted/50 text-muted-foreground ring-border',
};

const TONE_GLOW: Record<IconChipTone, string> = {
  primary: 'hover:shadow-primary/25',
  indigo: 'hover:shadow-indigo-500/25 dark:hover:shadow-indigo-400/20',
  amber: 'hover:shadow-amber-500/25 dark:hover:shadow-amber-400/20',
  emerald: 'hover:shadow-emerald-500/25 dark:hover:shadow-emerald-400/20',
  violet: 'hover:shadow-violet-500/25 dark:hover:shadow-violet-400/20',
  sky: 'hover:shadow-sky-500/25 dark:hover:shadow-sky-400/20',
  rose: 'hover:shadow-rose-500/25 dark:hover:shadow-rose-400/20',
  slate: 'hover:shadow-slate-500/20 dark:hover:shadow-slate-400/15',
  muted: 'hover:shadow-foreground/10',
};

const SIZES: Record<IconChipSize, string> = {
  sm: 'size-7 rounded-lg [&_svg]:size-3.5',
  md: 'size-9 rounded-xl [&_svg]:size-4',
  lg: 'size-11 rounded-2xl [&_svg]:size-[1.15rem]',
  xl: 'size-14 rounded-2xl [&_svg]:size-6',
  '2xl': 'size-16 rounded-2xl [&_svg]:size-7',
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
        'relative isolate inline-flex shrink-0 items-center justify-center bg-gradient-to-br to-transparent ring-1 ring-inset',
        'transition-[transform,box-shadow,filter] duration-300 ease-out',
        SIZES[size],
        ICON_CHIP_TONES[tone],
        interactive && ['hover:-translate-y-0.5 hover:shadow-lg', TONE_GLOW[tone]],
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-b from-white/70 via-white/10 to-transparent opacity-80 dark:from-white/12 dark:via-white/0 dark:opacity-60"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-1.5 -bottom-px h-px rounded-full bg-gradient-to-r from-transparent via-current to-transparent opacity-40"
      />
      <span className="relative z-10 flex items-center justify-center [&_svg]:drop-shadow-sm">
        {icon ?? children}
      </span>
    </span>
  );
}

'use client';

import { cn } from '@/utils/cn';
import { memo } from 'react';

interface LogoProps {
  className?: string;
  showTagline?: boolean;
  inverted?: boolean;
  iconOnly?: boolean;
}

const Logo = ({
  className = '',
  showTagline = false,
  inverted = false,
  iconOnly = false,
}: LogoProps) => (
  <div className={cn('flex items-center gap-2', className)}>
    <svg
      viewBox="0 0 40 40"
      className={cn('shrink-0', showTagline ? 'h-8 w-8' : iconOnly ? 'h-8 w-8' : 'h-10 w-10')}
      aria-hidden
    >
      <defs>
        <linearGradient id="tone-t-vert" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#818cf8" />
          <stop offset="50%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#c084fc" />
        </linearGradient>
        <linearGradient id="tone-t-bar" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="60%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#f59e0b" />
        </linearGradient>
      </defs>
      <rect x="14.5" y="12" width="11" height="26" rx="5.5" ry="5.5" fill="url(#tone-t-vert)" />
      <rect x="5" y="6" width="30" height="10" rx="5" ry="5" fill="url(#tone-t-bar)" />
    </svg>
    {!iconOnly && (
      <div className="flex flex-col justify-center gap-0 leading-tight">
        <span
          className={cn(
            'font-bold tracking-tight',
            showTagline ? 'text-base' : 'text-xl',
            inverted ? 'text-white' : 'text-foreground',
          )}
        >
          Tone
        </span>
        {showTagline && (
          <span
            className={cn(
              'text-[9px] font-medium uppercase tracking-widest',
              inverted ? 'text-white/50' : 'text-muted-foreground',
            )}
          >
            AI Voice Agent Builder
          </span>
        )}
      </div>
    )}
  </div>
);

export default memo(Logo);

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
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      className="h-7 w-7 shrink-0"
      aria-hidden
    >
      <rect width="32" height="32" rx="7" fill="#18202e" />
      <g fill={inverted ? '#ffffff' : '#ffffff'}>
        <rect x="7" y="13" width="2" height="6" rx="1" opacity="0.5" />
        <rect x="11" y="10" width="2" height="12" rx="1" opacity="0.75" />
        <rect x="15" y="7" width="2" height="18" rx="1" />
        <rect x="19" y="10" width="2" height="12" rx="1" opacity="0.75" />
        <rect x="23" y="13" width="2" height="6" rx="1" opacity="0.5" />
      </g>
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
      </div>
    )}
  </div>
);

export default memo(Logo);

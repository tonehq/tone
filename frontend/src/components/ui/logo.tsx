'use client';

import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  inverted?: boolean;
}

export function Logo({ className, size = 'md', showText = true, inverted = false }: LogoProps) {
  const sizes = {
    sm: { icon: 'h-6 w-6', text: 'text-base' },
    md: { icon: 'h-7 w-7', text: 'text-xl' },
    lg: { icon: 'h-9 w-9', text: 'text-2xl' },
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <ToneLogoSvg className={sizes[size].icon} />
      {showText && (
        <span
          className={cn(
            'font-bold tracking-tight',
            sizes[size].text,
            inverted ? 'text-white' : 'text-foreground',
          )}
        >
          Tone
        </span>
      )}
    </div>
  );
}

export function LogoIcon({ className }: { className?: string }) {
  return <ToneLogoSvg className={cn('h-7 w-7', className)} />;
}

function ToneLogoSvg({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('shrink-0', className)} aria-hidden>
      <defs>
        <linearGradient id="tone-wave" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <rect x="2" y="12" width="4" height="8" rx="2" fill="url(#tone-wave)" opacity="0.7" />
      <rect x="8" y="8" width="4" height="16" rx="2" fill="url(#tone-wave)" opacity="0.85" />
      <rect x="14" y="4" width="4" height="24" rx="2" fill="url(#tone-wave)" />
      <rect x="20" y="9" width="4" height="14" rx="2" fill="url(#tone-wave)" opacity="0.85" />
      <rect x="26" y="13" width="4" height="6" rx="2" fill="url(#tone-wave)" opacity="0.6" />
    </svg>
  );
}

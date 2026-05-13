'use client';

import { cn } from '@/utils/cn';

interface ToneLoaderProps {
  size?: 'sm' | 'default' | 'lg';
  label?: string;
  className?: string;
}

const SIZE_MAP = {
  sm: {
    ringSize: 'size-10',
    iconSize: 16,
    plate: 'size-5',
    labelText: 'text-[10px]',
    gap: 'gap-2',
  },
  default: {
    ringSize: 'size-14',
    iconSize: 22,
    plate: 'size-7',
    labelText: 'text-[11px]',
    gap: 'gap-3',
  },
  lg: {
    ringSize: 'size-20',
    iconSize: 32,
    plate: 'size-10',
    labelText: 'text-[12px]',
    gap: 'gap-4',
  },
} as const;

/**
 * Tone Mark — the loader's AI glyph.
 *
 * A 4-pointed AI sparkle drawn with smooth concave Bezier curves
 * (the "lens flare" silhouette used across modern AI products —
 * Gemini, Notion AI, Copilot). Paired with a smaller offset
 * companion sparkle so the mark reads as "AI generative" rather
 * than a static decoration.
 *
 *  • Main sparkle (full opacity) — primary AI signal
 *  • Companion twinkle (offset, ~55% opacity) — gives the mark
 *    a "magic / processing" feel
 *
 * `fill="currentColor"` so the entire glyph picks up `text-primary`
 * from the parent in both light + dark mode.
 */
function ToneMark({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Main AI sparkle — 4 points, smooth concave sides */}
      <path d="M11 2 C11 7.5 7.5 11 2 11 C7.5 11 11 14.5 11 20 C11 14.5 14.5 11 20 11 C14.5 11 11 7.5 11 2 Z" />
      {/* Companion twinkle, offset top-right */}
      <path
        d="M19 13.5 C19 15.4 18.4 16 16.5 16 C18.4 16 19 16.6 19 18.5 C19 16.6 19.6 16 21.5 16 C19.6 16 19 15.4 19 13.5 Z"
        opacity="0.55"
      />
    </svg>
  );
}

export default function ToneLoader({ size = 'default', label, className }: ToneLoaderProps) {
  const sizes = SIZE_MAP[size];

  return (
    <div
      role="status"
      aria-label={label ?? 'Loading'}
      className={cn('flex flex-col items-center', sizes.gap, className)}
    >
      <div className={cn('relative flex items-center justify-center', sizes.ringSize)}>
        {/* Ripple ring — primary, leading */}
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded-full border border-primary/30"
          style={{ animation: 'tone-loader-ring 2s ease-out infinite' }}
        />
        {/* Ripple ring — secondary, offset by 1s */}
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded-full border border-primary/20"
          style={{ animation: 'tone-loader-ring 2s ease-out 1s infinite' }}
        />

        {/* Pulsing Tone Mark plate — primary-tinted glow */}
        <span
          aria-hidden="true"
          className={cn(
            'relative flex items-center justify-center rounded-full bg-primary/15 text-primary shadow-sm shadow-primary/20 dark:bg-primary/25',
            sizes.plate,
          )}
          style={{ animation: 'tone-loader-mic 1.4s ease-in-out infinite' }}
        >
          <ToneMark size={sizes.iconSize} />
        </span>
      </div>

      {label && (
        <span
          className={cn('font-medium tracking-tight text-muted-foreground', sizes.labelText)}
          style={{ animation: 'tone-loader-label 1.8s ease-in-out infinite' }}
        >
          {label}
        </span>
      )}
    </div>
  );
}

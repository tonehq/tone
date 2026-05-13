'use client';

import { cn } from '@/utils/cn';
import { Server } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getProviderLogoUrl, TYPE_ICON_STYLES, TYPE_ICONS } from './constants';

interface ProviderLogoProps {
  /** Provider's internal name (lowercased) — e.g. "openai", "google", "elevenlabs". */
  providerName?: string | null;
  /** Used for the typed fallback tile when no logo is found. */
  serviceType?: string;
  /** Tailwind size class (e.g. 'size-10', 'size-7'). */
  className?: string;
  /** Inner image size in pixels. Defaults to fit the size class. */
  imgSize?: number;
  /** Visual scale: "default" applies a small inset padding, "tight" removes it. */
  variant?: 'default' | 'tight';
}

/**
 * Renders a provider's brand logo (via the PROVIDER_LOGOS map) on a
 * white plate so dark logos render in both light + dark mode. Falls
 * back to the typed icon tile (BrainCircuit / Mic / Volume2) when the
 * logo URL is missing or the image fails to load.
 */
export default function ProviderLogo({
  providerName,
  serviceType = '',
  className = 'size-10',
  imgSize,
  variant = 'default',
}: ProviderLogoProps) {
  const [failed, setFailed] = useState(false);
  const logoUrl = getProviderLogoUrl(providerName);
  const show = !!logoUrl && !failed;

  // Reset the failure state when the provider changes.
  useEffect(() => {
    setFailed(false);
  }, [logoUrl]);

  if (!show) {
    return (
      <div
        className={cn(
          'flex shrink-0 items-center justify-center overflow-hidden rounded-lg',
          TYPE_ICON_STYLES[serviceType] ?? 'bg-muted text-muted-foreground',
          className,
        )}
      >
        {TYPE_ICONS[serviceType] ?? <Server className="size-4" />}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-white dark:border-border/60',
        variant === 'default' ? 'p-1' : '',
        className,
      )}
    >
      <img
        src={logoUrl ?? ''}
        alt={providerName ?? 'Provider icon'}
        width={imgSize ?? 22}
        height={imgSize ?? 22}
        className="object-contain"
        style={imgSize ? { width: imgSize, height: imgSize } : undefined}
        onError={() => setFailed(true)}
      />
    </div>
  );
}

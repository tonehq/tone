'use client';

import { cn } from '@/utils/cn';
import { Check } from 'lucide-react';
import type { ReactNode } from 'react';

interface ProviderTileProps {
  icon?: ReactNode;
  iconBg: string;
  iconBorder: string;
  accentColor: string;
  name: string;
  /** Small uppercase eyebrow under the title (e.g. "OAuth", "MCP · OAuth", "API key"). */
  categoryLabel: ReactNode;
  description?: string;
  isInUse?: boolean;
  /** Dim the tile and drop the hover lift (used for unconfigured OAuth providers). */
  dimmed?: boolean;
  /** Call-to-action rendered at the foot of the tile (Connect / Add API key / …). */
  cta: ReactNode;
  /** Optional actions slot — rendered next to the "In use" badge. Used by the
   * OAuth catalog tiles to show an admin kebab menu (Edit / Delete). Channels
   * and other tile types omit it and the slot collapses. */
  actionsSlot?: ReactNode;
}

/**
 * Shared presentational card for a single integration provider. Used by every section of the
 * available-integrations catalog (OAuth, MCP, API key) so the tile chrome — accent glow, icon,
 * in-use badge, title, eyebrow, description, CTA slot — lives in one place.
 */
export default function ProviderTile({
  icon,
  iconBg,
  iconBorder,
  accentColor,
  name,
  categoryLabel,
  description,
  isInUse = false,
  dimmed = false,
  cta,
  actionsSlot,
}: ProviderTileProps) {
  return (
    <article
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-2xl border border-border/80 bg-card p-5 transition-all duration-200',
        !dimmed && ' hover:border-foreground/20',
        dimmed && 'opacity-80',
      )}
    >
      <span
        className={cn(
          'pointer-events-none absolute -right-12 -top-12 size-32 rounded-full blur-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-30',
          accentColor,
        )}
        aria-hidden
      />

      <header className="flex items-start justify-between gap-2">
        <div
          className={cn(
            'flex size-11 shrink-0 items-center justify-center rounded-xl border shadow-sm',
            iconBg,
            iconBorder,
          )}
        >
          {icon}
        </div>
        <div className="flex items-center gap-1.5">
          {isInUse && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
              <Check className="size-3" strokeWidth={2.5} />
              In use
            </span>
          )}
          {actionsSlot}
        </div>
      </header>

      <div className="mt-4 min-w-0 flex-1">
        <h3 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
          {name}
        </h3>
        <p className="mt-0.5 inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/80">
          {categoryLabel}
        </p>
        <p className="mt-2.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>

      <div className="mt-5">{cta}</div>
    </article>
  );
}

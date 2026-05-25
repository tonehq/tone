'use client';

import { CustomButton } from '@/components/shared';
import { API_KEY_PROVIDERS, OAUTH_PROVIDERS } from '@/constants/integrations';
import { getOAuthAuthorizeUrl } from '@/services/oauthService';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { ArrowUpRight, Check, Plus } from 'lucide-react';
import { useState } from 'react';

interface AvailableIntegrationsCatalogProps {
  onAddApiKey: (providerKey: string) => void;
  connectedSlugs?: Set<string>;
  configuredChannelTypes?: Set<string>;
}

export default function AvailableIntegrationsCatalog({
  onAddApiKey,
  connectedSlugs,
  configuredChannelTypes,
}: AvailableIntegrationsCatalogProps) {
  const [pendingProvider, setPendingProvider] = useState<string | null>(null);

  const handleConnectOAuth = async (providerKey: string) => {
    setPendingProvider(providerKey);
    try {
      const url = await getOAuthAuthorizeUrl(providerKey);
      window.location.href = url;
    } catch (err) {
      handleApiError(err);
      setPendingProvider(null);
    }
  };

  const tiles = [
    ...OAUTH_PROVIDERS.map((p) => ({
      ...p,
      action: () => handleConnectOAuth(p.key),
      buttonLabel: 'Connect',
      buttonIcon: <ArrowUpRight className="size-3.5" />,
      kind: 'oauth' as const,
      categoryLabel: 'OAuth',
      isInUse: connectedSlugs?.has(p.key) ?? false,
    })),
    ...API_KEY_PROVIDERS.map((p) => ({
      ...p,
      action: () => onAddApiKey(p.key),
      buttonLabel: 'Add API key',
      buttonIcon: <Plus className="size-3.5" />,
      kind: 'api_key' as const,
      categoryLabel: 'API key',
      isInUse: configuredChannelTypes?.has(p.key) ?? false,
    })),
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {tiles.map((tile) => (
        <article
          key={`${tile.kind}-${tile.key}`}
          className={cn(
            'group relative flex flex-col overflow-hidden rounded-2xl border border-border/80 bg-card p-5 transition-all duration-200',
            'hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-[0_8px_24px_-12px_rgba(0,0,0,0.12)]',
          )}
        >
          {/* Brand-color accent glow that intensifies on hover */}
          <span
            className={cn(
              'pointer-events-none absolute -right-12 -top-12 size-32 rounded-full blur-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-30',
              tile.accentColor,
            )}
            aria-hidden
          />

          <header className="flex items-start justify-between gap-2">
            <div
              className={cn(
                'flex size-11 shrink-0 items-center justify-center rounded-xl border shadow-sm',
                tile.iconBg,
                tile.iconBorder,
              )}
            >
              {tile.icon}
            </div>
            {tile.isInUse && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                <Check className="size-3" strokeWidth={2.5} />
                In use
              </span>
            )}
          </header>

          <div className="mt-4 min-w-0 flex-1">
            <div className="flex items-baseline gap-2">
              <h3 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
                {tile.name}
              </h3>
            </div>
            <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground/80">
              {tile.categoryLabel}
            </p>
            <p className="mt-2.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {tile.description}
            </p>
          </div>

          <div className="mt-5">
            <CustomButton
              type="default"
              size="sm"
              onClick={tile.action}
              loading={pendingProvider === tile.key}
              className="w-full justify-center gap-1.5"
            >
              {tile.buttonLabel}
              {tile.buttonIcon}
            </CustomButton>
          </div>
        </article>
      ))}
    </div>
  );
}

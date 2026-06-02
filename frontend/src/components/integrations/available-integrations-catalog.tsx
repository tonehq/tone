'use client';

import ProviderTile from '@/components/integrations/provider-tile';
import { CustomButton } from '@/components/shared';
import {
  API_KEY_PROVIDERS,
  OAUTH_PROVIDERS,
  PROVIDER_CATEGORY_LABELS,
  type ProviderCardConfig,
} from '@/constants/integrations';
import { getOAuthAuthorizeUrl } from '@/services/oauthService';
import type { OAuthCatalogProvider } from '@/types/oauth';
import { handleApiError } from '@/utils/helpers';
import { ArrowUpRight, Plus, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';

interface AvailableIntegrationsCatalogProps {
  onAddApiKey: (providerKey: string) => void;
  connectedSlugs?: Set<string>;
  configuredChannelTypes?: Set<string>;
  /** Backend catalog (configured + scopes). When absent, all OAuth providers render as available. */
  catalog?: OAuthCatalogProvider[];
}

const OAUTH_VISUAL_BY_KEY = OAUTH_PROVIDERS.reduce<Record<string, ProviderCardConfig>>(
  (acc, item) => {
    acc[item.key] = item;
    return acc;
  },
  {},
);

// Render order for category groups.
const CATEGORY_ORDER = ['google', 'productivity', 'dev_crm', 'other'];

interface OAuthTile extends ProviderCardConfig {
  configured: boolean;
  scopeCount: number;
}

export default function AvailableIntegrationsCatalog({
  onAddApiKey,
  connectedSlugs,
  configuredChannelTypes,
  catalog,
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

  // Build OAuth tiles from the catalog (source of truth for which providers exist + configured),
  // falling back to the static visual list when the catalog hasn't loaded yet.
  const oauthGroups = useMemo(() => {
    const source: OAuthTile[] = catalog?.length
      ? catalog.map((p) => {
          const visual = OAUTH_VISUAL_BY_KEY[p.slug];
          return {
            key: p.slug,
            name: visual?.name ?? p.display_name,
            description: visual?.description ?? p.description,
            icon: visual?.icon,
            iconBg: visual?.iconBg ?? 'bg-muted',
            iconBorder: visual?.iconBorder ?? 'border-border/50',
            accentColor: visual?.accentColor ?? 'bg-primary',
            category: (visual?.category ?? p.category) as ProviderCardConfig['category'],
            configured: p.configured,
            scopeCount: p.scopes?.length ?? 0,
          } as OAuthTile;
        })
      : OAUTH_PROVIDERS.map((p) => ({ ...p, configured: true, scopeCount: 0 }));

    const grouped = new Map<string, OAuthTile[]>();
    for (const tile of source) {
      const cat = tile.category ?? 'other';
      if (!grouped.has(cat)) grouped.set(cat, []);
      grouped.get(cat)!.push(tile);
    }
    return [...grouped.entries()].sort(
      (a, b) => CATEGORY_ORDER.indexOf(a[0]) - CATEGORY_ORDER.indexOf(b[0]),
    );
  }, [catalog]);

  return (
    <div className="space-y-7">
      {oauthGroups.map(([category, tiles]) => (
        <section key={category} className="space-y-3">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">
            {PROVIDER_CATEGORY_LABELS[category] ?? 'Other'}
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {tiles.map((tile) => (
              <ProviderTile
                key={`oauth-${tile.key}`}
                icon={tile.icon}
                iconBg={tile.iconBg}
                iconBorder={tile.iconBorder}
                accentColor={tile.accentColor}
                name={tile.name}
                description={tile.description}
                isInUse={connectedSlugs?.has(tile.key) ?? false}
                dimmed={!tile.configured}
                categoryLabel={
                  <>
                    OAuth
                    {tile.scopeCount > 0 && (
                      <span className="inline-flex items-center gap-0.5 normal-case tracking-normal text-muted-foreground/70">
                        <ShieldCheck className="size-3" />
                        {tile.scopeCount} {tile.scopeCount === 1 ? 'scope' : 'scopes'}
                      </span>
                    )}
                  </>
                }
                cta={
                  tile.configured ? (
                    <CustomButton
                      type="default"
                      size="sm"
                      onClick={() => handleConnectOAuth(tile.key)}
                      loading={pendingProvider === tile.key}
                      className="w-full justify-center gap-1.5"
                    >
                      Connect
                      <ArrowUpRight className="size-3.5" />
                    </CustomButton>
                  ) : (
                    <CustomButton
                      type="default"
                      size="sm"
                      disabled
                      className="w-full justify-center"
                      aria-label={`${tile.name} is not configured`}
                    >
                      Not configured
                    </CustomButton>
                  )
                }
              />
            ))}
          </div>
        </section>
      ))}

      {/* API-key providers (channels) */}
      <section className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">
          API key
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {API_KEY_PROVIDERS.map((tile) => (
            <ProviderTile
              key={`api-${tile.key}`}
              icon={tile.icon}
              iconBg={tile.iconBg}
              iconBorder={tile.iconBorder}
              accentColor={tile.accentColor}
              name={tile.name}
              description={tile.description}
              categoryLabel="API key"
              isInUse={configuredChannelTypes?.has(tile.key) ?? false}
              cta={
                <CustomButton
                  type="default"
                  size="sm"
                  onClick={() => onAddApiKey(tile.key)}
                  className="w-full justify-center gap-1.5"
                >
                  Add API key
                  <Plus className="size-3.5" />
                </CustomButton>
              }
            />
          ))}
        </div>
      </section>
    </div>
  );
}

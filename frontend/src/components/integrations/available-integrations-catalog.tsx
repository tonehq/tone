'use client';

import IntegrationLogo from '@/components/integrations/integration-logo';
import ProviderTile from '@/components/integrations/provider-tile';
import { getProviderLogoUrl } from '@/components/service-providers/constants';
import { ActionMenu, CustomButton } from '@/components/shared';
import {
  API_KEY_PROVIDERS,
  PROVIDER_CATEGORY_LABELS,
  type ProviderCardConfig,
} from '@/constants/integrations';
import { deleteAppIntegration } from '@/services/appIntegrationService';
import { getOAuthAuthorizeUrl } from '@/services/oauthService';
import type { OAuthCatalogProvider } from '@/types/oauth';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { ArrowUpRight, Pencil, Plus, ShieldCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

interface AvailableIntegrationsCatalogProps {
  onAddApiKey: (providerKey: string) => void;
  connectedSlugs?: Set<string>;
  configuredChannelTypes?: Set<string>;
  /** Backend catalog (configured + scopes). When absent, all OAuth providers render as available. */
  catalog?: OAuthCatalogProvider[];
  /** Called after a successful delete so the parent can refetch the catalog
   * and the removed tile disappears. Optional — if omitted, deletion still
   * works but the grid won't update until the next page load. */
  onCatalogChanged?: () => void;
}

// Render order for category groups.
const CATEGORY_ORDER = ['google', 'productivity', 'dev_crm', 'other'];

// Generic visual fallbacks for OAuth tiles. The DB-backed catalog doesn't
// carry icon assets, so every tile renders with the same neutral chrome —
// upgrade to ``icon_url``-driven imagery when admins start providing icons.
const OAUTH_TILE_DEFAULTS = {
  iconBg: 'bg-muted',
  iconBorder: 'border-border/50',
  accentColor: 'bg-primary',
} as const;

interface OAuthTile extends ProviderCardConfig {
  configured: boolean;
  scopeCount: number;
  /** ``app_integrations.id`` — present when the tile was sourced from the
   * backend catalog. Absent when we fall back to the static visual list. */
  id?: string;
  /** Default (seeded) rows are protected from deletion. */
  isDefault?: boolean;
  /** Admin-supplied logo URL from ``app_integrations.icon_url`` — takes
   *  precedence over the static frontend registry. */
  iconUrl?: string | null;
}

export default function AvailableIntegrationsCatalog({
  onAddApiKey,
  connectedSlugs,
  configuredChannelTypes,
  catalog,
  onCatalogChanged,
}: AvailableIntegrationsCatalogProps) {
  const router = useRouter();
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

  const handleEdit = (id: string) => {
    router.push(`/settings/integrations/edit/${id}`);
  };

  const handleDelete = async (id: string, displayName: string) => {
    try {
      await deleteAppIntegration(id);
      showToast.success(`${displayName} deleted`);
      onCatalogChanged?.();
    } catch (err) {
      handleApiError(err);
    }
  };

  // Build OAuth tiles directly from the DB-backed catalog — the previous
  // hardcoded fallback list was retired when ``OAUTH_PROVIDERS`` was emptied.
  const oauthGroups = useMemo(() => {
    const source: OAuthTile[] = (catalog ?? []).map((p) => {
      const resolvedLogoUrl = p.icon_url || getProviderLogoUrl(p.slug);
      return {
        key: p.slug,
        name: p.display_name,
        description: p.description,
        icon: undefined,
        // When a real brand mark is available, swap to a white plate so dark
        // logos render correctly in both light + dark mode (mirrors the
        // ``ProviderLogo`` styling used elsewhere).
        iconBg: resolvedLogoUrl ? 'bg-white' : OAUTH_TILE_DEFAULTS.iconBg,
        iconBorder: OAUTH_TILE_DEFAULTS.iconBorder,
        accentColor: OAUTH_TILE_DEFAULTS.accentColor,
        category: p.category as ProviderCardConfig['category'],
        configured: p.configured,
        scopeCount: p.scopes?.length ?? 0,
        id: p.id,
        isDefault: p.is_default,
        iconUrl: p.icon_url ?? null,
      };
    });

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
                icon={
                  <IntegrationLogo
                    slug={tile.key}
                    iconUrl={tile.iconUrl}
                    name={tile.name}
                    imgSize={22}
                  />
                }
                iconBg={tile.iconBg}
                iconBorder={tile.iconBorder}
                accentColor={tile.accentColor}
                name={tile.name}
                description={tile.description}
                isInUse={connectedSlugs?.has(tile.key) ?? false}
                dimmed={!tile.configured}
                actionsSlot={
                  tile.id ? (
                    <IntegrationTileActions
                      id={tile.id}
                      name={tile.name}
                      isDefault={!!tile.isDefault}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
                  ) : null
                }
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

// ─────────────────────────────────────────────────────────────────────
// Per-tile actions (admin kebab menu)
// ─────────────────────────────────────────────────────────────────────

interface IntegrationTileActionsProps {
  id: string;
  name: string;
  isDefault: boolean;
  onEdit: (id: string) => void;
  onDelete: (id: string, name: string) => Promise<void>;
}

/**
 * Renders the per-tile admin actions on the Available providers grid.
 *
 * Default (seeded) rows get an Edit-only icon button — the backend rejects
 * delete on those rows, so hiding the option is the cleaner UX than letting
 * the user see a destructive action that 400s. Admin-created rows get the
 * full :component:`ActionMenu` (Edit + Delete with built-in confirmation).
 */
function IntegrationTileActions({
  id,
  name,
  isDefault,
  onEdit,
  onDelete,
}: IntegrationTileActionsProps) {
  if (isDefault) {
    return (
      <CustomButton
        type="text"
        size="icon-sm"
        onClick={() => onEdit(id)}
        aria-label={`Edit ${name}`}
        className="text-muted-foreground hover:text-foreground"
      >
        <Pencil className="size-3.5" />
      </CustomButton>
    );
  }
  return (
    <ActionMenu
      onEdit={() => onEdit(id)}
      onDelete={() => onDelete(id, name)}
      itemName={name}
      deleteDescription={`This removes "${name}" from your catalog. Existing OAuth connections will be unlinked but kept. This cannot be undone.`}
    />
  );
}

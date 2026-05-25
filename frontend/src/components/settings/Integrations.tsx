'use client';

import { channelsAtom, fetchChannelsAtom, resetChannelsAtom } from '@/atoms/IntegrationAtom';
import { fetchOAuthAtom, oauthAtom, resetOAuthAtom } from '@/atoms/OAuthAtom';
import AvailableIntegrationsCatalog from '@/components/integrations/available-integrations-catalog';
import ChannelGrid, { type ChannelGridHandle } from '@/components/integrations/channel-grid';
import OAuthConnectionGrid from '@/components/integrations/oauth-connection-grid';
import { CustomButton } from '@/components/shared';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { useAtomValue, useSetAtom } from 'jotai';
import { Phone, Plug, RefreshCw, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef } from 'react';

const CATALOG_ANCHOR_ID = 'integrations-available-providers';
const OAUTH_AND_API_HINT = 'Pick any provider below to add it to your workspace';

function CountChip({ value, dim = false }: { value: number | null; dim?: boolean }) {
  if (value === null) return null;
  return (
    <span
      className={cn(
        'inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full px-1.5 text-[10px] font-semibold tabular-nums',
        dim ? 'bg-foreground/5 text-foreground/60' : 'bg-foreground/10 text-foreground/80',
      )}
    >
      {value}
    </span>
  );
}

interface IntegrationsProps {
  refreshKey?: string | null;
}

export default function Integrations({ refreshKey }: IntegrationsProps) {
  const channelGridRef = useRef<ChannelGridHandle | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const oauthState = useAtomValue(oauthAtom);
  const channelsState = useAtomValue(channelsAtom);

  const refetchOAuth = useSetAtom(fetchOAuthAtom);
  const refetchChannels = useSetAtom(fetchChannelsAtom);
  const resetOAuth = useSetAtom(resetOAuthAtom);
  const resetChannels = useSetAtom(resetChannelsAtom);

  useEffect(
    () => () => {
      resetOAuth();
      resetChannels();
    },
    [resetOAuth, resetChannels],
  );

  useEffect(() => {
    if (refreshKey) {
      refetchOAuth().catch((err) => handleApiError(err));
    }
  }, [refreshKey, refetchOAuth]);

  const handleAddApiKey = useCallback((providerKey: string) => {
    channelGridRef.current?.openAdd(providerKey);
  }, []);

  const handleRefreshAll = useCallback(() => {
    refetchOAuth().catch((err) => handleApiError(err));
    refetchChannels().catch((err) => handleApiError(err));
  }, [refetchOAuth, refetchChannels]);

  const handleScrollToCatalog = useCallback(() => {
    const el = document.getElementById(CATALOG_ANCHOR_ID);
    const root = scrollRef.current;
    if (!el || !root) return;
    root.scrollTo({ top: el.offsetTop - 16, behavior: 'smooth' });
  }, []);

  const connectedOAuthSlugs = useMemo(
    () => new Set(oauthState.items.map((i) => i.provider_slug)),
    [oauthState.items],
  );
  const configuredChannelTypes = useMemo(
    () => new Set(channelsState.items.map((i) => i.channel_type)),
    [channelsState.items],
  );

  const oauthCount = oauthState.initialized ? oauthState.items.length : null;
  const channelsCount = channelsState.initialized ? channelsState.items.length : null;
  const totalCount =
    oauthCount === null && channelsCount === null ? null : (oauthCount ?? 0) + (channelsCount ?? 0);

  const isRefreshing = oauthState.status === 'loading' || channelsState.status === 'loading';

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* ── Fixed page header ─────────────────────────────────── */}
      <header className="shrink-0 border-b border-border/60 bg-background">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-[22px] font-semibold leading-tight tracking-tight text-foreground">
              Integrations
            </h1>
            <p className="mt-1 max-w-xl text-xs leading-relaxed text-muted-foreground sm:text-sm">
              Connect services and manage credentials that power your voice agents.
            </p>
          </div>
          <CustomButton
            type="default"
            size="sm"
            onClick={handleRefreshAll}
            loading={isRefreshing}
            icon={<RefreshCw className="size-3.5" />}
            className="self-start sm:self-auto"
          >
            Refresh
          </CustomButton>
        </div>
      </header>

      {/* ── Scrollable content (the only thing that scrolls) ──── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-7xl space-y-8 px-6 pb-10 pt-6">
          {/* Available providers (catalog) */}
          <section id={CATALOG_ANCHOR_ID} className="space-y-4 scroll-mt-6">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-violet-500" strokeWidth={2.25} />
                <h2 className="text-[15px] font-semibold tracking-tight text-foreground">
                  Available providers
                </h2>
              </div>
              <p className="hidden text-xs text-muted-foreground sm:block">{OAUTH_AND_API_HINT}</p>
            </div>
            <AvailableIntegrationsCatalog
              onAddApiKey={handleAddApiKey}
              connectedSlugs={connectedOAuthSlugs}
              configuredChannelTypes={configuredChannelTypes}
            />
          </section>

          {/* Your integrations (workspace) */}
          <section className="relative overflow-hidden rounded-3xl border border-border/70 bg-gradient-to-b from-muted/40 to-muted/15 p-5 sm:p-6">
            <span
              aria-hidden
              className="pointer-events-none absolute -right-24 -top-24 size-64 rounded-full bg-violet-500/[0.06] blur-3xl"
            />

            <div className="relative mb-4 flex items-center gap-2">
              <h2 className="text-[15px] font-semibold tracking-tight text-foreground">
                Your integrations
              </h2>
              <CountChip value={totalCount} />
            </div>

            <Tabs defaultValue="services" className="relative w-full">
              <TabsList className="mb-5 bg-background/80 shadow-sm">
                <TabsTrigger value="services" className="gap-1.5 px-3">
                  <Plug className="size-3.5" />
                  <span>Services</span>
                  <CountChip value={oauthCount} dim />
                </TabsTrigger>
                <TabsTrigger value="channels" className="gap-1.5 px-3">
                  <Phone className="size-3.5" />
                  <span>Channels</span>
                  <CountChip value={channelsCount} dim />
                </TabsTrigger>
              </TabsList>

              <TabsContent value="services">
                <OAuthConnectionGrid onConnectAnother={handleScrollToCatalog} />
              </TabsContent>

              <TabsContent value="channels">
                <ChannelGrid controlRef={channelGridRef} />
              </TabsContent>
            </Tabs>
          </section>
        </div>
      </div>
    </div>
  );
}

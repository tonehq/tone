'use client';

import { disconnectOAuthAtom, fetchOAuthAtom, oauthAtom } from '@/atoms/OAuthAtom';
import { discoverMcpOAuth, getOAuthAuthorizeUrl } from '@/services/oauthService';
import type { OAuthConnection } from '@/types/oauth';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { AnimatePresence, motion } from 'framer-motion';
import { useAtomValue, useSetAtom } from 'jotai';
import { ArrowUp } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import OAuthConnectionCard, { cardVariants } from './oauth-connection-card';
import OAuthConnectionGridSkeleton from './oauth-connection-grid-skeleton';

// Generic MCP connections re-authorize through discovery; custom credentials (static bearer /
// client-credentials) have no interactive re-auth flow at all.
const MCP_SLUG_PREFIX = 'mcp:';
const CUSTOM_SLUG_PREFIX = 'custom:';

interface OAuthConnectionGridProps {
  emptyMessage?: string;
  onConnectAnother?: () => void;
  /** Provider slug → required scopes (from the catalog) for the scope-status badges. */
  requiredScopesByProvider?: Record<string, string[]>;
}

export default function OAuthConnectionGrid({
  emptyMessage = 'No services connected yet — pick one from "Browse providers" above.',
  onConnectAnother,
  requiredScopesByProvider,
}: OAuthConnectionGridProps) {
  const state = useAtomValue(oauthAtom);
  const fetchList = useSetAtom(fetchOAuthAtom);
  const disconnect = useSetAtom(disconnectOAuthAtom);

  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const [reconnectingProvider, setReconnectingProvider] = useState<string | null>(null);

  const handleReconnect = useCallback(async (connection: OAuthConnection) => {
    const provider = connection.provider_slug;
    // Custom credentials (static bearer / client-credentials) have no interactive re-auth flow.
    // The card already omits Reconnect for them, but guard here too so a non-catalog slug never
    // reaches the catalog authorize endpoint (which would 400 "Unsupported provider").
    if (provider.startsWith(CUSTOM_SLUG_PREFIX)) {
      showToast.error(
        'Custom credentials cannot be reconnected — recreate the credential instead.',
      );
      return;
    }
    setReconnectingProvider(provider);
    try {
      let url: string;
      if (provider.startsWith(MCP_SLUG_PREFIX)) {
        // Generic MCP connections aren't catalog providers, so the authorize endpoint can't
        // re-auth them — re-run discovery against the stored server URL instead.
        const serverUrl = connection.public_metadata?.server_url;
        if (!serverUrl) {
          showToast.error('Cannot reconnect: this MCP connection has no stored server URL.');
          setReconnectingProvider(null);
          return;
        }
        url = await discoverMcpOAuth(serverUrl, connection.label ?? undefined);
      } else {
        url = await getOAuthAuthorizeUrl(provider);
      }
      window.location.href = url;
    } catch (err) {
      handleApiError(err);
      setReconnectingProvider(null);
    }
  }, []);

  useEffect(() => {
    if (!state.initialized && state.status !== 'loading') {
      fetchList().catch((err) => handleApiError(err));
    }
  }, [state.initialized, state.status, fetchList]);

  const handleDisconnect = useCallback(
    async (id: string) => {
      setDisconnectingId(id);
      try {
        await disconnect(id);
        showToast.success('Account disconnected');
      } catch (err) {
        handleApiError(err);
      } finally {
        setDisconnectingId(null);
      }
    },
    [disconnect],
  );

  if (!state.initialized && state.status === 'loading') {
    return <OAuthConnectionGridSkeleton />;
  }

  const addRow = onConnectAnother ? (
    <button
      type="button"
      onClick={onConnectAnother}
      className={cn(
        'group flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-foreground/15 bg-transparent px-4 py-3 text-xs font-medium text-muted-foreground transition-all',
        'hover:border-foreground/30 hover:bg-background hover:text-foreground hover:shadow-sm',
      )}
    >
      <ArrowUp className="size-3.5 transition-transform group-hover:-translate-y-0.5" />
      Connect another service
    </button>
  ) : null;

  // Hide in-flight MCP discovery handshakes (pending) — they aren't usable connections yet.
  const connections = state.items.filter((c) => c.public_metadata?.status !== 'pending');

  if (state.initialized && connections.length === 0) {
    return (
      <div className="flex flex-col gap-2">
        <div className="rounded-xl border border-dashed border-border/70 bg-muted/20 px-4 py-6 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </div>
        {addRow}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <AnimatePresence initial={false}>
        {connections.map((connection) => (
          <motion.div
            key={connection.id}
            layout
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <OAuthConnectionCard
              connection={connection}
              onDisconnect={handleDisconnect}
              isDisconnecting={disconnectingId === connection.id}
              requiredScopes={requiredScopesByProvider?.[connection.provider_slug]}
              // Custom credentials have no interactive re-auth flow, so don't offer Reconnect.
              onReconnect={
                connection.provider_slug.startsWith(CUSTOM_SLUG_PREFIX)
                  ? undefined
                  : handleReconnect
              }
              isReconnecting={reconnectingProvider === connection.provider_slug}
            />
          </motion.div>
        ))}
      </AnimatePresence>

      {addRow}
    </div>
  );
}

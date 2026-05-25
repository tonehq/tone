'use client';

import { disconnectOAuthAtom, fetchOAuthAtom, oauthAtom } from '@/atoms/OAuthAtom';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { AnimatePresence, motion } from 'framer-motion';
import { useAtomValue, useSetAtom } from 'jotai';
import { ArrowUp } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import OAuthConnectionCard, { cardVariants } from './oauth-connection-card';
import OAuthConnectionGridSkeleton from './oauth-connection-grid-skeleton';

interface OAuthConnectionGridProps {
  emptyMessage?: string;
  onConnectAnother?: () => void;
}

export default function OAuthConnectionGrid({
  emptyMessage = 'No services connected yet — pick one from "Browse providers" above.',
  onConnectAnother,
}: OAuthConnectionGridProps) {
  const state = useAtomValue(oauthAtom);
  const fetchList = useSetAtom(fetchOAuthAtom);
  const disconnect = useSetAtom(disconnectOAuthAtom);

  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);

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

  if (state.initialized && state.items.length === 0) {
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
        {state.items.map((connection) => (
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
            />
          </motion.div>
        ))}
      </AnimatePresence>

      {addRow}
    </div>
  );
}

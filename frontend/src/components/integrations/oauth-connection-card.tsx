'use client';

import { getProviderLogoUrl } from '@/components/service-providers/constants';
import { CustomButton, ScopeStatus } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { formatRelative } from '@/utils/date';
import { cn } from '@/utils/cn';
import { normalizeScopes, shortScopeLabel } from '@/utils/scopes';
import { motion, type Variants } from 'framer-motion';
import { Clock, Mail, Unplug } from 'lucide-react';

import IntegrationLogo from './integration-logo';
import { getOAuthProviderVisual, humanizeSlug } from './providerVisuals';
import type { OAuthConnection } from '@/types/oauth';

const MAX_VISIBLE_SCOPES = 3;

export const cardVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.14 } },
};

interface OAuthConnectionCardProps {
  connection: OAuthConnection;
  onDisconnect: (id: string) => void | Promise<void>;
  isDisconnecting?: boolean;
  /** Scopes the provider requires (from the catalog) — drives the scope-status badge. */
  requiredScopes?: string[];
  /** Re-run the authorize/discovery flow to grant missing scopes or refresh an expired token. */
  onReconnect?: (connection: OAuthConnection) => void | Promise<void>;
  isReconnecting?: boolean;
}

export default function OAuthConnectionCard({
  connection,
  onDisconnect,
  isDisconnecting = false,
  requiredScopes,
  onReconnect,
  isReconnecting = false,
}: OAuthConnectionCardProps) {
  const visual = getOAuthProviderVisual(connection.provider_slug);
  // Catalog providers use their brand name; custom credentials show their user-given label.
  const displayName = visual?.name ?? connection.label ?? humanizeSlug(connection.provider_slug);
  const hasLogo = !!getProviderLogoUrl(connection.provider_slug);
  const email = connection.public_metadata?.user_email ?? null;
  const refreshed = formatRelative(connection.updated_at);
  const grantedScopes = normalizeScopes(connection.public_metadata?.scopes);
  const expiry = connection.public_metadata?.token_expiry ?? null;
  const isExpired = typeof expiry === 'number' && expiry > 0 && expiry * 1000 < Date.now();
  const visibleScopes = grantedScopes.slice(0, MAX_VISIBLE_SCOPES);
  const overflowCount = grantedScopes.length - visibleScopes.length;

  return (
    <motion.div
      layout
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-border/80 bg-card transition-all duration-200',
        'hover:border-foreground/20',
      )}
    >
      {/* Brand accent stripe down the left edge */}
      <span
        className={cn('absolute inset-y-0 left-0 w-1', visual?.accentColor ?? 'bg-emerald-500')}
        aria-hidden
      />

      <div className="flex items-center gap-4 py-4 pl-5 pr-4">
        <div
          className={cn(
            'flex size-11 shrink-0 items-center justify-center rounded-xl border shadow-sm',
            visual?.iconBg ?? (hasLogo ? 'bg-white' : 'bg-muted'),
            visual?.iconBorder ?? 'border-border/50',
          )}
        >
          {visual?.icon ?? <IntegrationLogo slug={connection.provider_slug} name={displayName} />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="truncate text-sm font-semibold tracking-tight text-foreground">
              {displayName}
            </h3>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500/60" />
                <span className="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
              </span>
              Connected
            </span>
          </div>
          <dl className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
            {email && (
              <div className="inline-flex min-w-0 items-center gap-1.5">
                <Mail className="size-3 shrink-0" />
                <dd className="truncate">{email}</dd>
              </div>
            )}
            <div className="inline-flex items-center gap-1.5">
              <Clock className="size-3 shrink-0" />
              <dd>Refreshed {refreshed}</dd>
            </div>
          </dl>

          {/* Scope pills + scope/health status */}
          {(grantedScopes.length > 0 || (requiredScopes?.length ?? 0) > 0 || isExpired) && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              {visibleScopes.map((scope) => (
                <Badge
                  key={scope}
                  variant="secondary"
                  className="font-normal text-[10px] text-muted-foreground"
                >
                  {shortScopeLabel(scope)}
                </Badge>
              ))}
              {overflowCount > 0 && (
                <Badge variant="outline" className="font-normal text-[10px] text-muted-foreground">
                  +{overflowCount} more
                </Badge>
              )}
              <ScopeStatus
                granted={grantedScopes}
                required={requiredScopes}
                expired={isExpired}
                onReconnect={onReconnect ? () => onReconnect(connection) : undefined}
                reconnecting={isReconnecting}
              />
            </div>
          )}
        </div>

        <CustomButton
          type="text"
          size="sm"
          onClick={() => onDisconnect(connection.id)}
          loading={isDisconnecting}
          className="shrink-0 gap-1.5 self-start text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <Unplug className="size-3.5" />
          Disconnect
        </CustomButton>
      </div>
    </motion.div>
  );
}

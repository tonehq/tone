'use client';

/**
 * Reusable OAuth connection status badge — the ONLY user-facing surface for
 * a token's health on the Tools + MCP pages.
 *
 * Design principle: users should never think about OAuth refresh. Runtime
 * silently refreshes on every real call (see
 * ``OAuthService.get_valid_access_token_for_connection``); deep readiness
 * also triggers a real refresh via the same path. The badge here just
 * reports what the DB knows and shows a "Reconnect" button ONLY when the
 * token is past expiry — the one situation the user genuinely has to act on.
 *
 * No "Test" affordance: manually testing a token is an implementation
 * detail. Runtime + deep readiness already cover it. Real production apps
 * (Slack, GitHub, Notion) follow this same pattern.
 */

import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import { getOAuthAuthorizeUrl } from '@/services/oauthService';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';

const EXPIRING_SOON_WINDOW_SECONDS = 15 * 60; // matches backend readiness buffer

type BadgeState = 'connected' | 'expiring' | 'expired';

interface Props {
  /** OAuth connection id — reserved for future admin/debug flows. Kept in
   * the props so downstream code has a stable identifier for the row's
   * connection even though the widget currently makes no use of it. */
  connectionId: string;
  /** Provider slug (google_calendar, hubspot, …). Required for the
   * Reconnect redirect; hidden if missing. */
  providerSlug?: string | null;
  /** Unix seconds of the current token's expiry, or ``null`` when the
   * provider doesn't declare one (static bearer credentials). */
  tokenExpiry?: number | null;
  /** Compact mode — smaller badge for tight layouts like the MCP card
   * footer or an eventual dense table cell. */
  compact?: boolean;
}

const OAuthConnectionStatus = ({ providerSlug, tokenExpiry, compact = false }: Props) => {
  const [isReconnecting, setIsReconnecting] = useState(false);

  const state: BadgeState = useMemo(() => {
    if (tokenExpiry == null) return 'connected';
    const nowSeconds = Math.floor(Date.now() / 1000);
    const remaining = tokenExpiry - nowSeconds;
    if (remaining <= 0) return 'expired';
    if (remaining <= EXPIRING_SOON_WINDOW_SECONDS) return 'expiring';
    return 'connected';
  }, [tokenExpiry]);

  const badge = BADGE_MAP[state];

  const handleReconnect = useCallback(async () => {
    if (!providerSlug) {
      showToast.error('Reconnect unavailable', 'No provider information on this connection.');
      return;
    }
    setIsReconnecting(true);
    try {
      const authUrl = await getOAuthAuthorizeUrl(providerSlug);
      window.location.href = authUrl;
    } catch (error) {
      setIsReconnecting(false);
      handleApiError(error);
    }
  }, [providerSlug]);

  // Reconnect only appears for the ``expired`` state — the one case where
  // runtime + deep readiness would have already tried to refresh and the
  // stored token is stale enough that user action is genuinely needed.
  // Green / amber rows show only the badge to keep the surface quiet.
  const showReconnect = state === 'expired' && !!providerSlug;

  return (
    <div className={compact ? 'flex items-center gap-1.5' : 'flex items-center gap-2'}>
      <span
        className={[
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5',
          compact ? 'text-[11px]' : 'text-xs',
          badge.className,
        ].join(' ')}
        aria-label={`OAuth status: ${badge.label}`}
      >
        {badge.icon}
        {badge.label}
      </span>

      {showReconnect ? (
        <CustomButton
          // Compact mode (MCP card footer, dense rows) → xs. Full mode
          // (Tools table) → sm so the Reconnect action stays visually on
          // par with the row's other controls instead of shrinking to
          // near-invisible next to the badge.
          type="link"
          size={compact ? 'xs' : 'sm'}
          onClick={handleReconnect}
          loading={isReconnecting}
          disabled={isReconnecting}
        >
          Reconnect
        </CustomButton>
      ) : null}
    </div>
  );
};

// ── Badge map ────────────────────────────────────────────────────────────────
// Kept as a plain object so the JSX above stays declarative. Tailwind classes
// use the project's semantic tokens (emerald/amber/destructive) so dark mode
// and theme changes flow automatically.

const BADGE_MAP: Record<BadgeState, { label: string; className: string; icon: React.ReactNode }> = {
  connected: {
    label: 'Connected',
    className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    icon: <CheckCircle2 className="size-3" />,
  },
  expiring: {
    label: 'Expiring soon',
    className: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400',
    icon: <AlertTriangle className="size-3" />,
  },
  expired: {
    label: 'Expired',
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    icon: <ShieldAlert className="size-3" />,
  },
};

export default OAuthConnectionStatus;

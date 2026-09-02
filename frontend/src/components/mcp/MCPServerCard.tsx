'use client';

import { ActionMenu, OAuthConnectionStatus } from '@/components/shared';
import { getProviderLogoUrl } from '@/components/service-providers/constants';
import { Card, CardContent } from '@/components/ui/card';
import type { MCPServer } from '@/types/mcp';
import { cn } from '@/utils/cn';
import { Radio, Server, Zap } from 'lucide-react';
import { useState } from 'react';

function getServerHostname(serverUrl: string | null | undefined): string | null {
  if (!serverUrl) return null;
  try {
    return new URL(serverUrl).hostname;
  } catch {
    return null;
  }
}

function getApexDomain(hostname: string): string {
  const parts = hostname.split('.');
  if (parts.length <= 2) return hostname;
  const lastTwo = parts.slice(-2).join('.');
  const dualTier = new Set(['co.uk', 'com.au', 'co.in', 'co.jp', 'com.br', 'co.nz', 'com.mx']);
  if (dualTier.has(lastTwo)) return parts.slice(-3).join('.');
  return lastTwo;
}

function getFaviconUrl(serverUrl: string | null | undefined): string | null {
  const hostname = getServerHostname(serverUrl);
  if (!hostname) return null;
  const apex = getApexDomain(hostname);
  return (
    getProviderLogoUrl(hostname) ??
    getProviderLogoUrl(apex) ??
    `https://www.google.com/s2/favicons?domain=${apex}&sz=64`
  );
}

interface MCPServerCardProps {
  server: MCPServer;
  onClick: () => void;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

const MCPServerCard: React.FC<MCPServerCardProps> = ({ server, onClick, onEdit, onDelete }) => {
  const [faviconFailed, setFaviconFailed] = useState(false);
  const faviconUrl = getFaviconUrl(server.server_url);
  const hostname = getServerHostname(server.server_url);
  const showFavicon = !!faviconUrl && !faviconFailed;

  const isShttp = server.transport_type === 'streamable_http';
  const transportLabel = isShttp ? 'Streamable HTTP' : 'SSE';
  const TransportIcon = isShttp ? Zap : Radio;

  return (
    <Card
      className={cn(
        'group relative h-full cursor-pointer gap-0 overflow-hidden rounded-2xl border-border py-0 shadow-sm',
        'transition-colors duration-150 hover:border-muted-foreground/30 hover:bg-accent/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      )}
      role="button"
      tabIndex={0}
      aria-label={`View tools for MCP server ${server.name}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <CardContent className="flex h-full flex-col p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-surface">
            {showFavicon ? (
              <img
                src={faviconUrl ?? ''}
                alt={hostname ? `${hostname} icon` : 'MCP server icon'}
                width={20}
                height={20}
                className="size-5 object-contain"
                onError={() => setFaviconFailed(true)}
              />
            ) : (
              <Server size={16} className="text-muted-foreground" />
            )}
          </div>

          <div className="min-w-0 flex-1 pt-0.5">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'size-1.5 shrink-0 rounded-full',
                  server.is_active ? 'bg-success' : 'bg-muted-foreground/40',
                )}
                aria-hidden
              />
              <p className="truncate text-[14px] font-medium leading-tight text-foreground">
                {server.name}
              </p>
            </div>
            <p className="mt-1.5 truncate font-mono text-[11.5px] text-muted-foreground">
              {hostname ?? server.server_url}
            </p>
          </div>

          <div
            onClick={(e) => e.stopPropagation()}
            className="opacity-60 transition-opacity group-hover:opacity-100"
          >
            <ActionMenu onEdit={onEdit} onDelete={onDelete} itemName={server.name} />
          </div>
        </div>

        <p className="mt-4 line-clamp-2 min-h-[38px] text-[13px] leading-relaxed text-muted-foreground">
          {server.description || (
            <span className="text-muted-foreground/60">No description provided.</span>
          )}
        </p>

        <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-3.5">
          <span className="inline-flex items-center gap-1.5 font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted-foreground">
            <TransportIcon className="size-3" />
            {transportLabel}
          </span>
          <span
            className={cn(
              'font-mono text-[10.5px] uppercase tracking-[0.14em]',
              server.is_active ? 'text-foreground' : 'text-muted-foreground',
            )}
          >
            {server.is_active ? 'Live' : 'Paused'}
          </span>
        </div>

        {server.oauth_connection ? (
          <div className="mt-3 border-t border-border pt-3" onClick={(e) => e.stopPropagation()}>
            <OAuthConnectionStatus
              connectionId={server.oauth_connection.id}
              providerSlug={server.oauth_connection.provider_slug}
              tokenExpiry={server.oauth_connection.token_expiry}
              compact
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
};

export default MCPServerCard;

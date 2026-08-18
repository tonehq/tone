'use client';

import { ActionMenu } from '@/components/shared';
import { getProviderLogoUrl } from '@/components/service-providers/constants';
import { Card, CardContent } from '@/components/ui/card';
import type { MCPServer } from '@/types/mcp';
import { cn } from '@/utils/cn';
import { Globe, Radio, Server, Zap } from 'lucide-react';
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
        'group relative h-full cursor-pointer gap-0 overflow-hidden border-border/80 py-0',
        'transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20',
        'hover:shadow-[0_10px_30px_-14px_rgba(2,132,199,0.35)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
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
      {/* Brand accent stripe + soft hover glow */}
      <span
        className={cn(
          'absolute inset-y-0 left-0 w-1 transition-colors',
          server.is_active ? 'bg-sky-500/70' : 'bg-muted-foreground/30',
        )}
        aria-hidden
      />
      <span
        className="pointer-events-none absolute -right-12 -top-12 size-32 rounded-full bg-sky-500 opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-15"
        aria-hidden
      />

      <CardContent className="flex h-full flex-col p-5 pl-6">
        {/* Header — favicon + name + hostname + actions */}
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-all group-hover:scale-[1.04]',
              showFavicon
                ? 'border-border/60 bg-white p-1.5'
                : 'border-sky-500/20 bg-sky-500/10 text-sky-600 dark:text-sky-400',
            )}
          >
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
              <Server size={16} />
            )}
          </div>

          <div className="min-w-0 flex-1 pt-0.5">
            <p className="truncate text-[14px] font-semibold leading-tight tracking-tight text-foreground">
              {server.name}
            </p>
            <p className="mt-1 flex items-center gap-1 text-[12px] text-muted-foreground">
              <Globe className="size-3 shrink-0 opacity-70" />
              <span className="truncate">{hostname ?? server.server_url}</span>
            </p>
          </div>

          <div
            onClick={(e) => e.stopPropagation()}
            className="opacity-60 transition-opacity group-hover:opacity-100"
          >
            <ActionMenu onEdit={onEdit} onDelete={onDelete} itemName={server.name} />
          </div>
        </div>

        {/* Description */}
        <p className="mt-4 line-clamp-2 min-h-[40px] text-[12.5px] leading-relaxed text-muted-foreground">
          {server.description || (
            <span className="italic text-muted-foreground/60">No description provided.</span>
          )}
        </p>

        {/* Footer — transport chip + status pill (icon + text, not colour alone) */}
        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[10.5px] font-medium text-muted-foreground ring-1 ring-inset ring-border/60">
            <TransportIcon className="size-3" />
            {transportLabel}
          </span>
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[10.5px] font-semibold',
              server.is_active
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : 'bg-muted text-muted-foreground',
            )}
          >
            <span className="relative inline-flex size-1.5">
              {server.is_active && (
                <span className="absolute inset-0 animate-ping rounded-full bg-emerald-500/60" />
              )}
              <span
                className={cn(
                  'relative inline-flex size-1.5 rounded-full',
                  server.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40',
                )}
              />
            </span>
            {server.is_active ? 'Live' : 'Paused'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

export default MCPServerCard;

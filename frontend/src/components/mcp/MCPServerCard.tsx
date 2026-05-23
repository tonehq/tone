'use client';

import { ActionMenu } from '@/components/shared';
import { Card, CardContent } from '@/components/ui/card';
import type { MCPServer } from '@/types/mcp';
import { cn } from '@/utils/cn';
import { Server } from 'lucide-react';
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
  return `https://www.google.com/s2/favicons?domain=${getApexDomain(hostname)}&sz=64`;
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
  const transportLabel = isShttp ? 'SHTTP' : 'SSE';

  return (
    <Card
      className="group relative cursor-pointer gap-0 overflow-hidden py-0 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <CardContent className="flex flex-col p-5">
        {/* Header — favicon + name + hostname + actions */}
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border transition-colors group-hover:border-foreground/20',
              showFavicon ? 'bg-white p-1 dark:border-border/60' : 'bg-muted/40 dark:bg-muted/30',
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
              <Server size={16} className="text-muted-foreground" />
            )}
          </div>

          <div className="min-w-0 flex-1 pt-0.5">
            <p className="truncate text-[14px] font-semibold leading-tight tracking-tight text-foreground">
              {server.name}
            </p>
            <p className="mt-1 truncate text-[12px] text-muted-foreground">
              {hostname ?? server.server_url}
            </p>
          </div>

          <div onClick={(e) => e.stopPropagation()}>
            <ActionMenu onEdit={onEdit} onDelete={onDelete} itemName={server.name} />
          </div>
        </div>

        {/* Description */}
        <p className="mt-4 line-clamp-2 min-h-[40px] text-[12.5px] leading-relaxed text-muted-foreground">
          {server.description || (
            <span className="italic text-muted-foreground/60">No description provided.</span>
          )}
        </p>

        {/* Footer — protocol + status with animated dot */}
        <div className="mt-auto flex items-center justify-between pt-4 text-[11.5px]">
          <span className="font-medium text-muted-foreground">{transportLabel}</span>
          <span
            className={cn(
              'inline-flex items-center gap-1.5',
              server.is_active ? 'text-foreground' : 'text-muted-foreground',
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

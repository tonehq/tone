'use client';

import { deleteMcpServerAtom, fetchMcpServersAtom, mcpServersAtom } from '@/atoms/MCPAtom';
import { ActionMenu, CustomButton, TextInput } from '@/components/shared';
import type { MCPServer } from '@/types/mcp';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Boxes, Plus, Search, Server } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

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
  // Common dual-tier TLDs (.co.uk, .com.au, etc.) — keep last 3 parts
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

export default function MCPListPage() {
  const router = useRouter();
  const [{ servers, loading }] = useAtom(mcpServersAtom);
  const [, fetchServers] = useAtom(fetchMcpServersAtom);
  const [, deleteServer] = useAtom(deleteMcpServerAtom);

  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchServers().catch(handleApiError);
  }, [fetchServers]);

  const filteredServers = useMemo(() => {
    if (!search.trim()) return servers;
    const q = search.toLowerCase();
    return servers.filter(
      (s) =>
        (s.name ?? '').toLowerCase().includes(q) ||
        (s.description ?? '').toLowerCase().includes(q) ||
        (s.server_url ?? '').toLowerCase().includes(q),
    );
  }, [servers, search]);

  const handleEdit = useCallback(
    (server: MCPServer) => {
      router.push(`/mcp/edit/${server.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (server: MCPServer) => {
      try {
        await deleteServer(server.id);
        showToast.success('MCP server deleted successfully');
        await fetchServers();
      } catch (error) {
        handleApiError(error);
      }
    },
    [deleteServer, fetchServers],
  );

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-background px-6 py-4">
        <div className="min-w-0">
          <h1 className="text-[18px] font-semibold tracking-tight text-foreground">MCP Servers</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Connect Model Context Protocol servers to extend your agents with external tools and
            resources.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={14} />}
          onClick={() => router.push('/mcp/create')}
        >
          Create MCP Server
        </CustomButton>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
        <div className="mx-auto max-w-[1280px] px-8 py-8">
          {servers.length > 0 && (
            <div className="mb-5 max-w-sm">
              <TextInput
                name="mcp-search"
                placeholder="Search MCP servers..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={<Search size={16} />}
              />
            </div>
          )}

          {loading && servers.length === 0 ? (
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-[160px] animate-pulse rounded-xl border border-border bg-background"
                />
              ))}
            </div>
          ) : filteredServers.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-background px-6 py-16 text-center">
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Boxes size={24} />
              </div>
              <h3 className="mt-4 text-[15px] font-semibold text-foreground">
                {search ? 'No MCP servers match your search' : 'No MCP servers yet'}
              </h3>
              <p className="mt-1.5 max-w-[420px] text-[13px] leading-relaxed text-muted-foreground">
                {search
                  ? 'Try a different search term.'
                  : 'Register a Model Context Protocol server to give your agents access to external tools, files, and live data.'}
              </p>
              {!search && (
                <CustomButton
                  type="primary"
                  icon={<Plus size={14} />}
                  onClick={() => router.push('/mcp/create')}
                  className="mt-5"
                >
                  Create MCP Server
                </CustomButton>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 xl:grid-cols-3">
              {filteredServers.map((server) => (
                <MCPServerCard
                  key={server.id}
                  server={server}
                  onClick={() => handleEdit(server)}
                  onEdit={() => handleEdit(server)}
                  onDelete={() => handleDelete(server)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface MCPServerCardProps {
  server: MCPServer;
  onClick: () => void;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

function MCPServerCard({ server, onClick, onEdit, onDelete }: MCPServerCardProps) {
  const [faviconFailed, setFaviconFailed] = useState(false);
  const faviconUrl = getFaviconUrl(server.server_url);
  const hostname = getServerHostname(server.server_url);
  const showFavicon = !!faviconUrl && !faviconFailed;

  const isShttp = server.transport_type === 'streamable_http';
  const transportLabel = isShttp ? 'SHTTP' : 'SSE';

  return (
    <div className="group relative">
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
          }
        }}
        className={cn(
          'relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border bg-background p-5 text-left transition-all duration-300',
          'border-border/60 shadow-sm dark:border-border/30 dark:bg-card dark:shadow-none',
          'hover:border-primary hover:bg-primary/[0.02] hover:shadow-md hover:shadow-primary/10',
          'dark:hover:border-primary dark:hover:bg-primary/[0.04] dark:hover:shadow-none',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        )}
      >
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

        {/* Footer — protocol (plain text) + status (plain text with animated dot) */}
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
      </div>
    </div>
  );
}

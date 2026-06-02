'use client';

import { deleteMcpServerAtom, fetchMcpServersAtom, mcpServersAtom } from '@/atoms/MCPAtom';
import MCPCardSkeleton from '@/components/mcp/MCPCardSkeleton';
import MCPEmptyState from '@/components/mcp/MCPEmptyState';
import MCPServerCard from '@/components/mcp/MCPServerCard';
import { CustomButton, SearchBar } from '@/components/shared';
import type { MCPServer } from '@/types/mcp';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { motion } from 'framer-motion';
import { useAtom } from 'jotai';
import { Plus, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

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

  const handleCreate = useCallback(() => {
    router.push('/mcp/create');
  }, [router]);

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
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">MCP Servers</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect Model Context Protocol servers to extend your agents with external tools and
            resources.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={handleCreate}>
          Create MCP Server
        </CustomButton>
      </div>

      {/* Toolbar */}
      {servers.length > 0 && (
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar
            placeholder="Search MCP servers..."
            value={search}
            onSearch={setSearch}
            debounceMs={300}
            containerClassName="max-w-xs flex-1"
          />
          {search && filteredServers.length > 0 && (
            <span className="text-xs text-muted-foreground tabular-nums">
              {filteredServers.length} of {servers.length} shown
            </span>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex min-h-0 flex-1 flex-col">
        {/* Loading state */}
        {loading && servers.length === 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <MCPCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && servers.length === 0 && <MCPEmptyState onCreate={handleCreate} />}

        {/* No search results */}
        {!loading && search && filteredServers.length === 0 && servers.length > 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-muted">
              <Search className="size-5 text-muted-foreground" />
            </div>
            <p className="text-sm text-foreground">
              No MCP servers matching &ldquo;{search}&rdquo;
            </p>
            <button
              type="button"
              onClick={() => setSearch('')}
              className="mt-3 text-[13px] font-medium text-primary hover:underline"
            >
              Clear search
            </button>
          </div>
        )}

        {/* Card grid */}
        {!loading && filteredServers.length > 0 && (
          <motion.div
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } },
            }}
          >
            {filteredServers.map((server) => (
              <motion.div
                key={server.id}
                className="h-full"
                variants={{
                  hidden: { opacity: 0, y: 12 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
                }}
              >
                <MCPServerCard
                  server={server}
                  onClick={() => handleEdit(server)}
                  onEdit={() => handleEdit(server)}
                  onDelete={() => handleDelete(server)}
                />
              </motion.div>
            ))}

            {/* Create new dashed card */}
            <motion.button
              type="button"
              onClick={handleCreate}
              aria-label="Create a new MCP server"
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
              }}
              whileHover={{ y: -2 }}
              className="group relative flex h-full min-h-[164px] cursor-pointer items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-border bg-card/40 transition-colors hover:border-sky-500/50 hover:bg-sky-500/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="flex flex-col items-center gap-2 p-8">
                <div className="flex size-11 items-center justify-center rounded-xl bg-sky-500/10 text-sky-600 transition-transform group-hover:scale-110 dark:text-sky-400">
                  <Plus className="size-5" />
                </div>
                <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground">
                  New MCP Server
                </span>
              </div>
            </motion.button>
          </motion.div>
        )}
      </div>
    </div>
  );
}

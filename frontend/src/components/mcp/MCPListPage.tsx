'use client';

import { deleteMcpServerAtom, fetchMcpServersAtom, mcpServersAtom } from '@/atoms/MCPAtom';
import MCPCardSkeleton from '@/components/mcp/MCPCardSkeleton';
import MCPEmptyState from '@/components/mcp/MCPEmptyState';
import MCPServerCard from '@/components/mcp/MCPServerCard';
import { CustomButton, TextInput } from '@/components/shared';
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
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Header */}
      <motion.div
        className="flex shrink-0 items-start justify-between gap-4 border-b border-border bg-background px-6 py-4"
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="min-w-0">
          <h1 className="text-[18px] font-semibold tracking-tight text-foreground">MCP Servers</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Connect Model Context Protocol servers to extend your agents with external tools and
            resources.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus size={14} />} onClick={handleCreate}>
          Create MCP Server
        </CustomButton>
      </motion.div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
        <div className="mx-auto max-w-[1280px] px-8 py-8">
          {/* Search */}
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
                visible: { transition: { staggerChildren: 0.04, delayChildren: 0.15 } },
              }}
            >
              {filteredServers.map((server) => (
                <motion.div
                  key={server.id}
                  variants={{
                    hidden: { opacity: 0, y: 12 },
                    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
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
                variants={{
                  hidden: { opacity: 0, y: 12 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
                }}
                whileHover={{ y: -2 }}
                className="group relative flex min-h-[150px] cursor-pointer items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-border bg-background/40 transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
              >
                <div className="flex flex-col items-center gap-2 p-8">
                  <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 transition-transform group-hover:scale-110">
                    <Plus className="size-5 text-primary" />
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
    </div>
  );
}

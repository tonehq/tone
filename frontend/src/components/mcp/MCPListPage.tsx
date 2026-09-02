'use client';

import { deleteMcpServerAtom } from '@/atoms/MCPAtom';
import MCPCardSkeleton from '@/components/mcp/MCPCardSkeleton';
import MCPEmptyState from '@/components/mcp/MCPEmptyState';
import MCPServerCard from '@/components/mcp/MCPServerCard';
import { mcpListConfig } from '@/components/mcp/mcpListConfig';
import { SORT_OPTIONS } from '@/components/mcp/mcpConstants';
import {
  CustomButton,
  FacetFilterBar,
  FacetFilterDrawer,
  IconChip,
  useFacetedList,
} from '@/components/shared';
import SelectInput from '@/components/shared/SelectInput';
import type { MCPServer } from '@/types/mcp';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { motion } from 'framer-motion';
import { useAtom } from 'jotai';
import { Loader2, Plus, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';

export default function MCPListPage() {
  const router = useRouter();
  const [, deleteServer] = useAtom(deleteMcpServerAtom);

  const fl = useFacetedList(mcpListConfig);
  const servers = fl.rows;
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [sortValue, setSortValue] = useState('created_at:desc');

  const handleSort = useCallback(
    (value: string) => {
      setSortValue(value);
      const [field, order] = value.split(':');
      fl.handleSortChange({ field, order: order as 'asc' | 'desc' });
    },
    [fl],
  );

  const handleCreate = useCallback(() => {
    router.push('/mcp/create');
  }, [router]);

  const handleViewTools = useCallback(
    (server: MCPServer) => {
      router.push(`/mcp/${server.id}/tools`);
    },
    [router],
  );

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
        fl.refresh();
      } catch (error) {
        handleApiError(error);
      }
    },
    [deleteServer, fl],
  );

  // Keep the toolbar visible during the initial skeleton load too; only hide it
  // once we know there are genuinely no servers and no active filters.
  const showToolbar = fl.listLoading || fl.total > 0 || fl.hasActiveFilters;
  const isInitialLoading = fl.listLoading && servers.length === 0;
  const noServersAtAll = !fl.listLoading && servers.length === 0 && !fl.hasActiveFilters;
  const noMatches = !fl.listLoading && servers.length === 0 && fl.hasActiveFilters;

  return (
    <div className="animate-page mx-auto flex h-full min-h-0 w-full max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-muted-foreground">
            Build
          </p>
          <div className="flex items-baseline gap-3">
            <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
              MCP Servers
            </h1>
            {fl.total > 0 && (
              <span className="font-mono text-[13px] tabular-nums text-muted-foreground">
                {fl.total}
              </span>
            )}
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Connect Model Context Protocol servers to extend your agents with external tools and
            resources.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={15} />}
          className="h-10"
          onClick={handleCreate}
        >
          Create MCP server
        </CustomButton>
      </div>

      {/* Toolbar */}
      {showToolbar && (
        <FacetFilterBar
          fields={fl.tokenFields}
          tokens={fl.tokens}
          onTokensChange={fl.setTokens}
          onClear={fl.clearAll}
          showClear={fl.hasActiveFilters}
          placeholder="Search MCP servers… (e.g. name:clickup)"
          drawerFilterCount={fl.drawerFilterCount}
          onOpenDrawer={() => setFilterDrawerOpen(true)}
          rightSlot={
            <SelectInput
              name="mcp-sort"
              options={SORT_OPTIONS}
              value={sortValue}
              onValueChange={handleSort}
              size="sm"
              triggerClassName="min-w-[170px]"
            />
          }
        />
      )}

      {/* Content */}
      <div className="flex min-h-0 flex-1 flex-col">
        {isInitialLoading && (
          <>
            <div
              role="status"
              aria-live="polite"
              className="mb-4 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground"
            >
              <Loader2 className="size-3 animate-spin" aria-hidden />
              Loading MCP servers
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <MCPCardSkeleton key={i} />
              ))}
            </div>
          </>
        )}

        {noServersAtAll && <MCPEmptyState onCreate={handleCreate} />}

        {noMatches && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="mb-4 inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
              <Search className="size-5" strokeWidth={1.75} />
            </span>
            <p className="text-sm text-foreground">No MCP servers match your filters</p>
            <CustomButton
              type="link"
              onClick={fl.clearAll}
              className="!h-auto p-0 mt-3 text-[13px] font-medium text-primary hover:underline"
            >
              Clear filters
            </CustomButton>
          </div>
        )}

        {/* Card grid */}
        {!fl.listLoading && servers.length > 0 && (
          <motion.div
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } },
            }}
          >
            {servers.map((server) => (
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
                  onClick={() => handleViewTools(server)}
                  onEdit={() => handleEdit(server)}
                  onDelete={() => handleDelete(server)}
                />
              </motion.div>
            ))}

            {/* Create new dashed card */}
            <motion.div
              className="h-full"
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
              }}
              whileHover={{ y: -2 }}
            >
              <CustomButton
                type="text"
                onClick={handleCreate}
                aria-label="Create a new MCP server"
                className="group relative flex !h-full min-h-[164px] w-full cursor-pointer items-center justify-center overflow-hidden !rounded-xl border-2 border-dashed border-border bg-card/40 !px-0 !py-0 transition-colors hover:border-sky-500/50 hover:!bg-sky-500/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:!ring-sky-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                <div className="flex flex-col items-center gap-2 p-8">
                  <IconChip
                    icon={<Plus strokeWidth={1.75} />}
                    tone="sky"
                    size="lg"
                    className="transition-transform duration-300 group-hover:scale-110"
                  />
                  <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground">
                    New MCP Server
                  </span>
                </div>
              </CustomButton>
            </motion.div>
          </motion.div>
        )}
      </div>

      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter MCP servers by status and transport."
        sections={mcpListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />
    </div>
  );
}

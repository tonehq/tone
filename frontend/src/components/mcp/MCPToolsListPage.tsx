'use client';

import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import CountChip from '@/components/mcp/tools/CountChip';
import EmptyState from '@/components/mcp/tools/EmptyState';
import { AppLoader, CustomButton, CustomTable, TokenSearchBar } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { useGoBack } from '@/hooks/useGoBack';
import { discoverMcpTools, getMcpServer } from '@/services/mcpServerService';
import type { CustomTableColumn, SearchToken, TokenSearchField } from '@/types/components';
import type { MCPServer, MCPTool } from '@/types/mcp';
import { handleApiError } from '@/utils/helpers';

interface MCPToolsListPageProps {
  serverId: string;
}

export default function MCPToolsListPage({ serverId }: MCPToolsListPageProps) {
  const onBack = useGoBack('/mcp');

  const [server, setServer] = useState<MCPServer | null>(null);
  const [serverError, setServerError] = useState(false);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loadingServer, setLoadingServer] = useState(true);
  const [loadingTools, setLoadingTools] = useState(true);
  const [search, setSearch] = useState('');

  const fetchSeqRef = useRef(0);

  const loadTools = useCallback(async () => {
    const seq = ++fetchSeqRef.current;
    setLoadingTools(true);
    try {
      const result = await discoverMcpTools(serverId);
      if (seq !== fetchSeqRef.current) return;
      setTools(result.tools ?? []);
    } catch (error) {
      if (seq !== fetchSeqRef.current) return;
      handleApiError(error);
      setTools([]);
    } finally {
      if (seq === fetchSeqRef.current) setLoadingTools(false);
    }
  }, [serverId]);

  useEffect(() => {
    let cancelled = false;
    setLoadingServer(true);
    setServerError(false);
    getMcpServer(serverId)
      .then((data) => {
        if (!cancelled) setServer(data);
      })
      .catch((error) => {
        if (cancelled) return;
        setServerError(true);
        handleApiError(error);
      })
      .finally(() => {
        if (!cancelled) setLoadingServer(false);
      });
    return () => {
      cancelled = true;
    };
  }, [serverId]);

  useEffect(() => {
    void loadTools();
    return () => {
      // Bump the sequence so any in-flight loadTools response is ignored.
      fetchSeqRef.current += 1;
    };
  }, [loadTools]);

  const trimmedSearch = search.trim();
  const filteredTools = useMemo(() => {
    if (!trimmedSearch) return tools;
    const q = trimmedSearch.toLowerCase();
    return tools.filter(
      (t) => t.name.toLowerCase().includes(q) || (t.description ?? '').toLowerCase().includes(q),
    );
  }, [tools, trimmedSearch]);

  // Token-bar "Name" field — a value dropdown sourced from the loaded tools.
  const searchFields = useMemo<TokenSearchField[]>(
    () => [
      {
        key: 'name',
        label: 'Name',
        type: 'enum',
        fetchValues: () => Promise.resolve([...new Set(tools.map((t) => t.name))].sort()),
      },
    ],
    [tools],
  );
  const searchTokens = useMemo<SearchToken[]>(
    () => (search ? [{ field: 'name', value: search }] : []),
    [search],
  );
  const handleSearchTokens = useCallback((tokens: SearchToken[]) => {
    const last = [...tokens].reverse().find((t) => t.field === 'name');
    setSearch(last?.value ?? '');
  }, []);

  const columns = useMemo<CustomTableColumn<MCPTool>[]>(
    () => [
      {
        key: 'name',
        dataIndex: 'name',
        title: 'Name',
        width: 'w-auto',
        render: (_val, record) => (
          <div className="min-w-0">
            <p className="truncate font-mono text-[13px] font-medium text-foreground">
              {record.name}
            </p>
            {record.description && (
              <p className="mt-1 line-clamp-2 whitespace-normal text-[12px] leading-relaxed text-muted-foreground">
                {record.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: 'method',
        title: 'Method',
        align: 'left',
        width: 'w-[110px]',
        render: () => (
          <span className="inline-flex rounded-md bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700 dark:bg-blue-500/15 dark:text-blue-400">
            POST
          </span>
        ),
      },
      {
        key: 'params',
        title: 'Params',
        align: 'left',
        width: 'w-[15%]',
        render: (_val, record) => (
          <CountChip count={Object.keys(record.parameters ?? {}).length} label="param" tone="sky" />
        ),
      },
      {
        key: 'required',
        title: 'Required',
        align: 'left',
        width: 'w-[15%]',
        render: (_val, record) => (
          <CountChip count={record.required?.length ?? 0} label="required" tone="amber" noun />
        ),
      },
    ],
    [],
  );

  const total = tools.length;
  const hasFilter = !!trimmedSearch;
  const visibleCount = filteredTools.length;

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={onBack}
            aria-label="Back to MCP servers"
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                {loadingServer
                  ? 'Tools'
                  : (server?.name ?? (serverError ? 'Server unavailable' : 'Tools'))}
              </h1>
              {total > 0 && (
                <Badge
                  variant="secondary"
                  className="text-xs tabular-nums"
                  aria-label={
                    hasFilter ? `${visibleCount} of ${total} tools shown` : `${total} tools`
                  }
                >
                  {hasFilter ? `${visibleCount} / ${total}` : total}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {serverError && !loadingServer
                ? 'Could not load this MCP server. It may have been deleted or you may not have access.'
                : 'Tools exposed by this MCP server and available to your voice agents.'}
            </p>
          </div>
        </div>
        <CustomButton
          type="default"
          icon={<RefreshCw className="size-4" />}
          onClick={loadTools}
          loading={loadingTools}
          disabled={loadingTools}
        >
          Refresh
        </CustomButton>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <TokenSearchBar
          fields={searchFields}
          value={searchTokens}
          onChange={handleSearchTokens}
          placeholder="Search tools… (e.g. name:get_weather)"
          className="w-full sm:max-w-xs"
        />
      </div>

      {/* Table */}
      <div className="relative flex min-h-0 flex-1 flex-col">
        <CustomTable<MCPTool>
          className="[&_table]:table-fixed"
          columns={columns}
          dataSource={filteredTools}
          rowKey="name"
          loading={loadingTools}
          emptyState={<EmptyState hasFilter={hasFilter} />}
        />

        {loadingServer && !server && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-background/40">
            <AppLoader label="Loading server..." className="min-h-0" />
          </div>
        )}
      </div>
    </div>
  );
}

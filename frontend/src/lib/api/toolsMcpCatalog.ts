import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

import { listMcpServers } from '@/services/mcpServerService';
import { listOAuthConnections } from '@/services/oauthService';
import { getAllTools } from '@/services/toolService';
import type { MCPServer } from '@/types/mcp';
import type { OAuthConnection } from '@/types/oauth';
import type { Tool } from '@/types/tool';

export interface ToolsMcpCatalog {
  tools: Tool[];
  mcpServers: MCPServer[];
  connections: OAuthConnection[];
}

export const toolsMcpCatalogKeys = {
  all: () => ['tools-mcp-catalog'] as const,
};

/**
 * The tools/MCP/OAuth catalog is fetched as ONE unit (previously a single
 * `Promise.all` behind one `loading` flag) so the combined loading + error
 * semantics stay identical: any one request failing leaves every list empty
 * and surfaces one toast, exactly like the rejected `Promise.all` did.
 */
async function fetchToolsMcpCatalog(): Promise<ToolsMcpCatalog> {
  const [tools, mcpServers, connections] = await Promise.all([
    getAllTools(),
    listMcpServers(),
    listOAuthConnections(),
  ]);
  return { tools, mcpServers, connections };
}

export function useToolsMcpCatalog() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: toolsMcpCatalogKeys.all(),
    queryFn: fetchToolsMcpCatalog,
    retry: false,
  });

  // A credential created inline from a picker row is prepended to the cached
  // connection list (deduped by id) so it's immediately selectable across every
  // attachment — mirrors the old `setOauthConnections` local-state update.
  const addConnection = useCallback(
    (created: OAuthConnection) => {
      qc.setQueryData<ToolsMcpCatalog>(toolsMcpCatalogKeys.all(), (prev) =>
        prev
          ? {
              ...prev,
              connections: prev.connections.some((c) => c.id === created.id)
                ? prev.connections
                : [created, ...prev.connections],
            }
          : prev,
      );
    },
    [qc],
  );

  return { ...query, addConnection };
}

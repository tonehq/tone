import { deleteMcpServer, getAllMcpServers, upsertMcpServer } from '@/services/mcpServerService';
import type { MCPServer, MCPServerUpsertPayload, MCPServersState } from '@/types/mcp';
import { atom } from 'jotai';

const mcpServersAtom = atom<MCPServersState>({
  servers: [],
  loading: false,
});

const fetchMcpServersAtom = atom(null, async (_get, set) => {
  set(mcpServersAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const servers = await getAllMcpServers();
    set(mcpServersAtom, { servers: servers ?? [], loading: false });
  } catch (error) {
    set(mcpServersAtom, (prev) => ({ ...prev, servers: prev.servers ?? [], loading: false }));
    throw error;
  }
});

const upsertMcpServerAtom = atom(
  null,
  async (_get, _set, payload: MCPServerUpsertPayload): Promise<MCPServer> =>
    await upsertMcpServer(payload),
);

const deleteMcpServerAtom = atom(null, async (_get, _set, mcpServerId: number) => {
  await deleteMcpServer(mcpServerId);
});

export { mcpServersAtom, fetchMcpServersAtom, upsertMcpServerAtom, deleteMcpServerAtom };

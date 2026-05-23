import { deleteTool, getAllTools, upsertTool } from '@/services/toolService';
import type { Tool, ToolUpsertPayload, ToolsState } from '@/types/tool';
import { atom } from 'jotai';

const toolsAtom = atom<ToolsState>({
  tools: [],
  loading: false,
});

const fetchToolsAtom = atom(null, async (_get, set) => {
  set(toolsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const tools = await getAllTools();
    set(toolsAtom, { tools: tools ?? [], loading: false });
  } catch (error) {
    set(toolsAtom, (prev) => ({ ...prev, tools: prev.tools ?? [], loading: false }));
    throw error;
  }
});

const upsertToolAtom = atom(
  null,
  async (_get, _set, payload: ToolUpsertPayload): Promise<Tool> => await upsertTool(payload),
);

const deleteToolAtom = atom(null, async (_get, _set, toolId: string) => {
  await deleteTool(toolId);
});

export { toolsAtom, fetchToolsAtom, upsertToolAtom, deleteToolAtom };

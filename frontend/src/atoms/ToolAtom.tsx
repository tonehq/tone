import { createTool, deleteTool, getAllTools, updateTool } from '@/services/toolService';
import type { Tool, ToolCreatePayload, ToolsState, ToolUpdatePayload } from '@/types/tool';
import { atom } from 'jotai';

const toolsAtom = atom<ToolsState>({
  tools: [],
  loading: false,
});

const fetchToolsAtom = atom(null, async (_get, set) => {
  set(toolsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const tools = await getAllTools();
    set(toolsAtom, { tools, loading: false });
  } catch (error) {
    set(toolsAtom, (prev) => ({ ...prev, loading: false }));
    throw error;
  }
});

const createToolAtom = atom(
  null,
  async (_get, _set, payload: ToolCreatePayload): Promise<Tool> => await createTool(payload),
);

const updateToolAtom = atom(
  null,
  async (
    _get,
    _set,
    { toolId, payload }: { toolId: number; payload: ToolUpdatePayload },
  ): Promise<Tool> => await updateTool(toolId, payload),
);

const deleteToolAtom = atom(null, async (_get, _set, toolId: number) => {
  await deleteTool(toolId);
});

export { toolsAtom, fetchToolsAtom, createToolAtom, updateToolAtom, deleteToolAtom };

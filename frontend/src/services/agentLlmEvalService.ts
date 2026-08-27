import axiosInstance from '@/utils/axios';

import type {
  AgentLlmEvalRunDetail,
  AgentLlmEvalScenario,
  BulkCreateScenariosPayload,
  BulkDeleteScenariosPayload,
  BulkDeleteScenariosResponse,
  CompareRunsPayload,
  CompareRunsResponse,
  CreateFolderPayload,
  CreateFolderResponse,
  DeleteFolderPayload,
  DeleteFolderResponse,
  GenerateScenariosPayload,
  GenerateScenariosResponse,
  ListFoldersResponse,
  ListRunsRequest,
  ListRunsResponse,
  ListScenariosRequest,
  ListScenariosResponse,
  RenameFolderPayload,
  RenameFolderResponse,
  ScenarioInput,
  ScenarioPatch,
  TriggerRunPayload,
  TriggerRunResponse,
} from '@/types/agentLlmEval';

// All Level-2 (agent-LLM) eval HTTP goes through here so components never
// axios.post directly. Mirrors the router endpoints under
// `/agents/{agent_id}/llm-evals/...`.

const base = (agentId: string) => `/agents/${agentId}/llm-evals`;

// ── Scenarios ────────────────────────────────────────────────────────────

export const listAgentLlmEvalScenarios = async (
  agentId: string,
  body: ListScenariosRequest = {},
): Promise<ListScenariosResponse> => {
  const res = await axiosInstance.post<ListScenariosResponse>(
    `${base(agentId)}/scenarios/list`,
    body,
  );
  return res.data;
};

export const createAgentLlmEvalScenario = async (
  agentId: string,
  input: ScenarioInput,
): Promise<AgentLlmEvalScenario> => {
  const res = await axiosInstance.post<AgentLlmEvalScenario>(`${base(agentId)}/scenarios`, input);
  return res.data;
};

export const createAgentLlmEvalScenariosBulk = async (
  agentId: string,
  payload: BulkCreateScenariosPayload,
): Promise<{ items: AgentLlmEvalScenario[]; created: number }> => {
  const res = await axiosInstance.post<{ items: AgentLlmEvalScenario[]; created: number }>(
    `${base(agentId)}/scenarios/bulk`,
    payload,
  );
  return res.data;
};

export const uploadAgentLlmEvalScenariosCsv = async (
  agentId: string,
  file: File,
): Promise<{ items: AgentLlmEvalScenario[]; created: number }> => {
  const form = new FormData();
  form.append('file', file);
  const res = await axiosInstance.post<{ items: AgentLlmEvalScenario[]; created: number }>(
    `${base(agentId)}/scenarios/upload-csv`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data;
};

export const updateAgentLlmEvalScenario = async (
  agentId: string,
  scenarioId: string,
  patch: ScenarioPatch,
): Promise<AgentLlmEvalScenario> => {
  const res = await axiosInstance.put<AgentLlmEvalScenario>(
    `${base(agentId)}/scenarios/${scenarioId}`,
    patch,
  );
  return res.data;
};

export const deleteAgentLlmEvalScenariosBulk = async (
  agentId: string,
  payload: BulkDeleteScenariosPayload,
): Promise<BulkDeleteScenariosResponse> => {
  const res = await axiosInstance.post<BulkDeleteScenariosResponse>(
    `${base(agentId)}/scenarios/bulk_delete`,
    payload,
  );
  return res.data;
};

export const deleteAgentLlmEvalScenario = async (
  agentId: string,
  scenarioId: string,
): Promise<{ deleted: string }> => {
  const res = await axiosInstance.delete<{ deleted: string }>(
    `${base(agentId)}/scenarios/${scenarioId}`,
  );
  return res.data;
};

export const generateAgentLlmEvalScenarios = async (
  agentId: string,
  payload: GenerateScenariosPayload = {},
): Promise<GenerateScenariosResponse> => {
  const res = await axiosInstance.post<GenerateScenariosResponse>(
    `${base(agentId)}/scenarios/generate`,
    payload,
  );
  return res.data;
};

// ── Runs ─────────────────────────────────────────────────────────────────

export const triggerAgentLlmEvalRun = async (
  agentId: string,
  payload: TriggerRunPayload = {},
): Promise<TriggerRunResponse> => {
  const res = await axiosInstance.post<TriggerRunResponse>(`${base(agentId)}/runs`, payload);
  return res.data;
};

export const listAgentLlmEvalRuns = async (
  agentId: string,
  params: ListRunsRequest = {},
): Promise<ListRunsResponse> => {
  const res = await axiosInstance.get<ListRunsResponse>(`${base(agentId)}/runs`, {
    params,
  });
  return res.data;
};

export const getAgentLlmEvalRunDetail = async (
  agentId: string,
  runId: string,
): Promise<AgentLlmEvalRunDetail> => {
  const res = await axiosInstance.get<AgentLlmEvalRunDetail>(`${base(agentId)}/runs/${runId}`);
  return res.data;
};

export const compareAgentLlmEvalRuns = async (
  agentId: string,
  payload: CompareRunsPayload,
): Promise<CompareRunsResponse> => {
  const res = await axiosInstance.post<CompareRunsResponse>(
    `${base(agentId)}/runs/compare`,
    payload,
  );
  return res.data;
};

// ── Folders ──────────────────────────────────────────────────────────────

export const listAgentLlmEvalFolders = async (agentId: string): Promise<ListFoldersResponse> => {
  const res = await axiosInstance.get<ListFoldersResponse>(`${base(agentId)}/folders`);
  return res.data;
};

export const createAgentLlmEvalFolder = async (
  agentId: string,
  payload: CreateFolderPayload,
): Promise<CreateFolderResponse> => {
  const res = await axiosInstance.post<CreateFolderResponse>(`${base(agentId)}/folders`, payload);
  return res.data;
};

export const renameAgentLlmEvalFolder = async (
  agentId: string,
  payload: RenameFolderPayload,
): Promise<RenameFolderResponse> => {
  const res = await axiosInstance.post<RenameFolderResponse>(
    `${base(agentId)}/folders/rename`,
    payload,
  );
  return res.data;
};

export const deleteAgentLlmEvalFolder = async (
  agentId: string,
  payload: DeleteFolderPayload,
): Promise<DeleteFolderResponse> => {
  const res = await axiosInstance.post<DeleteFolderResponse>(
    `${base(agentId)}/folders/delete`,
    payload,
  );
  return res.data;
};

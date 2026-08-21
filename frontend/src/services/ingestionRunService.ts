import axiosInstance from '@/utils/axios';

import type {
  CreateIngestionRunPayload,
  CreateIngestionRunResponse,
  PipelineOptions,
} from '@/types/pipelineOptions';
import type {
  IngestionRun,
  ListIngestionRunChunksParams,
  ListIngestionRunsParams,
  PaginatedIngestionRunChunks,
  PaginatedIngestionRuns,
} from '@/types/ingestionRun';

// All ingestion-run HTTP flows through here so components never `axios.post`
// directly. Mirrors backend endpoints under `/knowledge-base/...`.

export const listIngestionRuns = async (
  uploadId: string,
  params: ListIngestionRunsParams = {},
): Promise<PaginatedIngestionRuns> => {
  const body: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') body[k] = v;
  }
  const res = await axiosInstance.post<PaginatedIngestionRuns>(
    `/knowledge-base/${uploadId}/runs/list`,
    body,
  );
  return res.data;
};

export const activateIngestionRun = async (
  uploadId: string,
  runId: string,
): Promise<IngestionRun> => {
  const res = await axiosInstance.post<IngestionRun>(
    `/knowledge-base/${uploadId}/runs/${runId}/activate`,
  );
  return res.data;
};

export interface AgentKbActiveRunPayload {
  active_ingestion_pipeline_run_id: string | null;
}

export interface AgentKnowledgeBaseRow {
  id: string;
  agent_id: string;
  knowledge_base_id: string;
  agent_config_id: string | null;
  active_ingestion_pipeline_run_id: string | null;
}

export const setAgentKbActiveRun = async (
  agentId: string,
  kbId: string,
  runId: string | null,
): Promise<AgentKnowledgeBaseRow> => {
  const res = await axiosInstance.put<AgentKnowledgeBaseRow>(
    `/knowledge-base/agents/${agentId}/knowledge-bases/${kbId}/active-run`,
    { active_ingestion_pipeline_run_id: runId } satisfies AgentKbActiveRunPayload,
  );
  return res.data;
};

export const getPipelineOptions = async (): Promise<PipelineOptions> => {
  const res = await axiosInstance.get<PipelineOptions>('/knowledge-base/pipeline-options');
  return res.data;
};

export const createCustomIngestionRun = async (
  uploadId: string,
  payload: CreateIngestionRunPayload,
): Promise<CreateIngestionRunResponse> => {
  const res = await axiosInstance.post<CreateIngestionRunResponse>(
    `/knowledge-base/${uploadId}/runs`,
    payload,
  );
  return res.data;
};

export const listIngestionRunChunks = async (
  uploadId: string,
  runId: string,
  params: ListIngestionRunChunksParams = {},
): Promise<PaginatedIngestionRunChunks> => {
  const query: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') query[k] = v as string | number;
  }
  const res = await axiosInstance.get<PaginatedIngestionRunChunks>(
    `/knowledge-base/${uploadId}/runs/${runId}/chunks`,
    { params: query },
  );
  return res.data;
};

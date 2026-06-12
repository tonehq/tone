import axiosInstance from '@/utils/axios';
import type {
  WorkflowDetail,
  WorkflowGraph,
  WorkflowSummary,
  WorkflowVersionSummary,
  ValidationIssue,
} from '@/types/workflow';

export const listWorkflows = async (): Promise<WorkflowSummary[]> => {
  const res = await axiosInstance.get<WorkflowSummary[]>('/workflow/list');
  return Array.isArray(res.data) ? res.data : [];
};

export const createWorkflow = async (
  name: string,
  description?: string,
): Promise<WorkflowDetail> => {
  const res = await axiosInstance.post<WorkflowDetail>('/workflow/create', { name, description });
  return res.data;
};

export const getWorkflow = async (workflowId: string): Promise<WorkflowDetail> => {
  const res = await axiosInstance.get<WorkflowDetail>('/workflow/get', {
    params: { workflow_id: workflowId },
  });
  return res.data;
};

export const saveWorkflowDraft = async (
  workflowId: string,
  graph: WorkflowGraph,
  expectedChecksum?: string | null,
): Promise<WorkflowDetail> => {
  const res = await axiosInstance.post<WorkflowDetail>('/workflow/save_draft', {
    workflow_id: workflowId,
    graph,
    expected_checksum: expectedChecksum ?? null,
  });
  return res.data;
};

export const validateWorkflow = async (
  graph: WorkflowGraph,
): Promise<{ is_valid: boolean; errors: ValidationIssue[] }> => {
  const res = await axiosInstance.post('/workflow/validate', { graph });
  return res.data;
};

export const publishWorkflow = async (workflowId: string): Promise<WorkflowDetail> => {
  const res = await axiosInstance.post<WorkflowDetail>('/workflow/publish', {
    workflow_id: workflowId,
  });
  return res.data;
};

export const listWorkflowVersions = async (
  workflowId: string,
): Promise<WorkflowVersionSummary[]> => {
  const res = await axiosInstance.get<WorkflowVersionSummary[]>('/workflow/list_versions', {
    params: { workflow_id: workflowId },
  });
  return Array.isArray(res.data) ? res.data : [];
};

export const deleteWorkflow = async (workflowId: string): Promise<{ success: boolean }> => {
  const res = await axiosInstance.delete('/workflow/delete', {
    params: { workflow_id: workflowId },
  });
  return res.data;
};

export const importVapiWorkflow = async (
  name: string,
  graph: Record<string, unknown>,
  description?: string,
): Promise<WorkflowDetail> => {
  const res = await axiosInstance.post<WorkflowDetail>('/workflow/import_vapi', {
    name,
    description,
    graph,
  });
  return res.data;
};

export const exportVapiWorkflow = async (workflowId: string): Promise<Record<string, unknown>> => {
  const res = await axiosInstance.get('/workflow/export_vapi', {
    params: { workflow_id: workflowId },
  });
  return res.data;
};

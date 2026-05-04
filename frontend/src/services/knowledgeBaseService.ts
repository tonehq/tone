import axiosInstance from '@/utils/axios';

export interface GetDocumentsParams {
  agent_id?: number;
  name?: string;
  sort?: string; // e.g. "-created_at" (desc) or "created_at" (asc)
  page?: number;
  page_size?: number;
}

export const getDocuments = async (params?: GetDocumentsParams) => {
  const res = await axiosInstance.post('/document/get_documents', params ?? {});
  return res.data;
};

export const uploadDocuments = async (agentId: number | string, files: File[]) => {
  const formData = new FormData();
  formData.append('agent_id', String(agentId));
  files.forEach((file) => formData.append('files', file));
  const res = await axiosInstance.post('/document/upload_document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const deleteDocuments = async (documentIds: number[]) => {
  const params = new URLSearchParams();
  documentIds.forEach((id) => params.append('document_ids', String(id)));
  await axiosInstance.delete(`/document/delete_document?${params.toString()}`);
};

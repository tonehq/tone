import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { contactKeys } from '@/lib/api/queryKeys';
import { toListBody, usePaginatedList } from '@/lib/api/usePaginatedList';
import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';
import type {
  ContactSchema,
  ContactSchemaDeleteResult,
  ContactSchemaDetail,
  ContactSchemaUpdateResult,
  CreateSchemaFieldPayload,
  CreateSchemaPayload,
  SchemaField,
  UpdateSchemaFieldPayload,
  UpdateSchemaPayload,
} from '@/types/contactSchema';
import axios from '@/utils/axios';

/**
 * Thin typed wrapper over the org-level `/contact-schemas` + `/schema-fields` endpoints.
 * Schemas are reusable across directories/syncs; setting a directory's default is done
 * via the directories client (`PATCH /contact-directories/{id}`), NOT here.
 */
export const schemasApi = {
  list: async (params: PaginatedListParams = {}): Promise<PaginatedResponse<ContactSchema>> => {
    const { data } = await axios.post<PaginatedResponse<ContactSchema>>(
      '/contact-schemas/list',
      toListBody(params),
    );
    return data;
  },
  get: async (id: string): Promise<ContactSchemaDetail> => {
    const { data } = await axios.get<ContactSchemaDetail>(`/contact-schemas/${id}`);
    return data;
  },
  create: async (payload: CreateSchemaPayload): Promise<ContactSchema> => {
    const { data } = await axios.post<ContactSchema>('/contact-schemas', payload);
    return data;
  },
  update: async (id: string, payload: UpdateSchemaPayload): Promise<ContactSchemaUpdateResult> => {
    const { data } = await axios.patch<ContactSchemaUpdateResult>(
      `/contact-schemas/${id}`,
      payload,
    );
    return data;
  },
  remove: async (id: string): Promise<ContactSchemaDeleteResult> => {
    const { data } = await axios.delete<ContactSchemaDeleteResult>(`/contact-schemas/${id}`);
    return data;
  },
  createField: async (
    schemaId: string,
    payload: CreateSchemaFieldPayload,
  ): Promise<SchemaField> => {
    const { data } = await axios.post<SchemaField>(`/contact-schemas/${schemaId}/fields`, payload);
    return data;
  },
  updateField: async (fieldId: string, payload: UpdateSchemaFieldPayload): Promise<SchemaField> => {
    const { data } = await axios.patch<SchemaField>(`/schema-fields/${fieldId}`, payload);
    return data;
  },
  removeField: async (fieldId: string): Promise<{ ok: boolean }> => {
    const { data } = await axios.delete<{ ok: boolean }>(`/schema-fields/${fieldId}`);
    return data;
  },
};

/** Paginated org-schema list. */
export function useSchemasList(params: PaginatedListParams = {}) {
  return usePaginatedList<ContactSchema>(
    contactKeys.schemas.list(params),
    () => schemasApi.list(params),
    params,
  );
}

/** One schema with its active fields + `referenced_by` counts. */
export function useSchema(id: string | null | undefined) {
  return useQuery({
    queryKey: contactKeys.schemas.detail(id ?? ''),
    queryFn: () => schemasApi.get(id as string),
    enabled: !!id,
  });
}

export function useCreateSchema() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSchemaPayload) => schemasApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: contactKeys.schemas.lists() }),
  });
}

export function useUpdateSchema() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateSchemaPayload }) =>
      schemasApi.update(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: contactKeys.schemas.lists() });
      qc.invalidateQueries({ queryKey: contactKeys.schemas.detail(id) });
    },
  });
}

export function useDeleteSchema() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schemasApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: contactKeys.schemas.lists() });
      // A schema may be a directory's default; refresh directories too.
      qc.invalidateQueries({ queryKey: contactKeys.directories.lists() });
    },
  });
}

export function useCreateSchemaField() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ schemaId, payload }: { schemaId: string; payload: CreateSchemaFieldPayload }) =>
      schemasApi.createField(schemaId, payload),
    onSuccess: (_data, { schemaId }) =>
      qc.invalidateQueries({ queryKey: contactKeys.schemas.detail(schemaId) }),
  });
}

export function useUpdateSchemaField() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      fieldId,
      payload,
    }: {
      fieldId: string;
      /** The parent schema id — needed only to invalidate its detail query. */
      schemaId: string;
      payload: UpdateSchemaFieldPayload;
    }) => schemasApi.updateField(fieldId, payload),
    onSuccess: (_data, { schemaId }) =>
      qc.invalidateQueries({ queryKey: contactKeys.schemas.detail(schemaId) }),
  });
}

export function useDeleteSchemaField() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fieldId }: { fieldId: string; schemaId: string }) =>
      schemasApi.removeField(fieldId),
    onSuccess: (_data, { schemaId }) =>
      qc.invalidateQueries({ queryKey: contactKeys.schemas.detail(schemaId) }),
  });
}

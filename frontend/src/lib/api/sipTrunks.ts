import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  SipCarrierPhoneNumber,
  SipTrunk,
  SipTrunkPayload,
  SipTrunkPhoneNumber,
} from '@/types/sipTrunk';
import axios from '@/utils/axios';

export const sipTrunkKeys = {
  all: () => ['sip-trunks'] as const,
  lists: () => ['sip-trunks', 'list'] as const,
  detail: (id: string) => ['sip-trunks', 'detail', id] as const,
  carriers: () => ['sip-trunks', 'carriers'] as const,
  phoneNumbers: (id: string) => ['sip-trunks', 'phone-numbers', id] as const,
  carrierNumbers: (id: string) => ['sip-trunks', 'carrier-numbers', id] as const,
};

export const sipTrunksApi = {
  list: async (): Promise<SipTrunk[]> => {
    const { data } = await axios.post<SipTrunk[]>('/sip-trunk/list', {});
    return data ?? [];
  },
  get: async (trunkId: string, includeAuth = false): Promise<SipTrunk> => {
    const { data } = await axios.get<SipTrunk>('/sip-trunk/get', {
      params: { trunk_id: trunkId, include_auth: includeAuth },
    });
    return data;
  },
  carriers: async (): Promise<string[]> => {
    const { data } = await axios.get<string[]>('/sip-trunk/carriers');
    return data ?? [];
  },
  create: async (payload: SipTrunkPayload): Promise<SipTrunk> => {
    const { data } = await axios.post<SipTrunk>('/sip-trunk/create', payload);
    return data;
  },
  update: async (trunkId: string, payload: SipTrunkPayload): Promise<SipTrunk> => {
    const { data } = await axios.put<SipTrunk>('/sip-trunk/update', payload, {
      params: { trunk_id: trunkId },
    });
    return data;
  },
  remove: async (trunkId: string): Promise<void> => {
    await axios.delete('/sip-trunk/delete', { params: { trunk_id: trunkId } });
  },
  provision: async (trunkId: string): Promise<SipTrunk> => {
    const { data } = await axios.post<SipTrunk>('/sip-trunk/provision', null, {
      params: { trunk_id: trunkId },
    });
    return data;
  },
  phoneNumbers: async (trunkId: string): Promise<SipTrunkPhoneNumber[]> => {
    const { data } = await axios.get<SipTrunkPhoneNumber[]>('/sip-trunk/phone_numbers', {
      params: { trunk_id: trunkId },
    });
    return data ?? [];
  },
  carrierPhoneNumbers: async (trunkId: string): Promise<SipCarrierPhoneNumber[]> => {
    const { data } = await axios.get<SipCarrierPhoneNumber[]>('/sip-trunk/carrier_phone_numbers', {
      params: { trunk_id: trunkId },
    });
    return data ?? [];
  },
  attachNumber: async (
    trunkId: string,
    number: string,
    label?: string | null,
  ): Promise<SipTrunkPhoneNumber> => {
    const { data } = await axios.post<SipTrunkPhoneNumber>(
      '/sip-trunk/attach_number',
      { number, label: label ?? null },
      { params: { trunk_id: trunkId } },
    );
    return data;
  },
  detachNumber: async (trunkId: string, number: string): Promise<void> => {
    await axios.delete('/sip-trunk/detach_number', {
      params: { trunk_id: trunkId, number },
    });
  },
};

export function useSipTrunks(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: sipTrunkKeys.lists(),
    queryFn: sipTrunksApi.list,
    enabled: options?.enabled ?? true,
  });
}

export function useSipTrunk(trunkId: string | null | undefined, includeAuth = false) {
  return useQuery({
    queryKey: sipTrunkKeys.detail(trunkId ?? ''),
    queryFn: () => sipTrunksApi.get(trunkId as string, includeAuth),
    enabled: !!trunkId,
  });
}

export function useSipCarriers() {
  return useQuery({
    queryKey: sipTrunkKeys.carriers(),
    queryFn: sipTrunksApi.carriers,
    staleTime: Infinity,
  });
}

export function useSipTrunkPhoneNumbers(trunkId: string | null | undefined) {
  return useQuery({
    queryKey: sipTrunkKeys.phoneNumbers(trunkId ?? ''),
    queryFn: () => sipTrunksApi.phoneNumbers(trunkId as string),
    enabled: !!trunkId,
  });
}

export function useCreateSipTrunk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SipTrunkPayload) => sipTrunksApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() }),
  });
}

export function useUpdateSipTrunk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trunkId, payload }: { trunkId: string; payload: SipTrunkPayload }) =>
      sipTrunksApi.update(trunkId, payload),
    onSuccess: (_data, { trunkId }) => {
      qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() });
      qc.invalidateQueries({ queryKey: sipTrunkKeys.detail(trunkId) });
    },
  });
}

export function useDeleteSipTrunk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trunkId: string) => sipTrunksApi.remove(trunkId),
    onSuccess: () => qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() }),
  });
}

export function useProvisionSipTrunk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trunkId: string) => sipTrunksApi.provision(trunkId),
    onSuccess: (_data, trunkId) => {
      qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() });
      qc.invalidateQueries({ queryKey: sipTrunkKeys.detail(trunkId) });
    },
  });
}

export function useAttachSipNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      trunkId,
      number,
      label,
    }: {
      trunkId: string;
      number: string;
      label?: string | null;
    }) => sipTrunksApi.attachNumber(trunkId, number, label),
    onSuccess: (_data, { trunkId }) => {
      qc.invalidateQueries({ queryKey: sipTrunkKeys.phoneNumbers(trunkId) });
      qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() });
    },
  });
}

export function useDetachSipNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trunkId, number }: { trunkId: string; number: string }) =>
      sipTrunksApi.detachNumber(trunkId, number),
    onSuccess: (_data, { trunkId }) => {
      qc.invalidateQueries({ queryKey: sipTrunkKeys.phoneNumbers(trunkId) });
      qc.invalidateQueries({ queryKey: sipTrunkKeys.lists() });
    },
  });
}

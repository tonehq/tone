'use client';

import { useAtom } from 'jotai';
import { useCallback, useState } from 'react';

import {
  deleteProviderModelAtom,
  deleteServiceAtom,
  fetchServiceAtom,
  upsertModelProviderAtom,
  upsertProviderModelAtom,
  upsertServiceAtom,
} from '@/atoms/ServicesAtom';
import { getModelProvider, listProviderCatalog } from '@/services/servicesService';
import type { ModelUpsertPayload } from '@/services/servicesService';
import type {
  ModelProvider,
  ModelProviderUpsertPayload,
  ModelRow,
  ProviderModel,
  Service,
  ServiceUpsertPayload,
} from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface DeleteKeyTarget {
  id: string;
  label: string | null;
  provider: string;
}

interface UseModelActionsArgs {
  /** Re-fetch the list + facets after a mutation. */
  refresh: () => void;
  /** Close the row-detail drawer so editor drawers don't stack over it. */
  closeDetail: () => void;
}

/**
 * Orchestrates the edit/delete flows launched from the model-row detail drawer,
 * reusing the existing ModelForm / ModelProviderEdit / ApiKeyEdit drawers and
 * the shared service atoms. Keeps ModelsTablePage thin: the page renders the
 * drawers from this state; all side effects live here.
 */
export function useModelActions({ refresh, closeDetail }: UseModelActionsArgs) {
  const [, upsertProviderModel] = useAtom(upsertProviderModelAtom);
  const [, deleteProviderModel] = useAtom(deleteProviderModelAtom);
  const [, upsertModelProvider] = useAtom(upsertModelProviderAtom);
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, deleteService] = useAtom(deleteServiceAtom);
  const [, fetchService] = useAtom(fetchServiceAtom);

  // Model editor
  const [modelEditOpen, setModelEditOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ProviderModel | null>(null);
  const [modelProviderId, setModelProviderId] = useState<string | null>(null);
  const [savingModel, setSavingModel] = useState(false);

  // Model creator (flat page — provider chosen in the drawer)
  const [addModelOpen, setAddModelOpen] = useState(false);
  const [providerOptions, setProviderOptions] = useState<{ id: string; display_name: string }[]>(
    [],
  );
  const [savingNewModel, setSavingNewModel] = useState(false);

  // Provider editor
  const [providerEditOpen, setProviderEditOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ModelProvider | null>(null);
  const [providerEditLoading, setProviderEditLoading] = useState(false);
  const [savingProvider, setSavingProvider] = useState(false);

  // API-key editor
  const [keyEditOpen, setKeyEditOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<Service | null>(null);
  const [keyEditLoading, setKeyEditLoading] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  // Delete confirmations
  const [deleteModelTarget, setDeleteModelTarget] = useState<ModelRow | null>(null);
  const [deletingModel, setDeletingModel] = useState(false);
  const [deleteKeyTarget, setDeleteKeyTarget] = useState<DeleteKeyTarget | null>(null);
  const [deletingKey, setDeletingKey] = useState(false);

  // ── model ──────────────────────────────────────────────────────────────
  const editModel = useCallback(
    (m: ModelRow) => {
      setModelProviderId(m.provider.id);
      setEditingModel(m);
      setModelEditOpen(true);
      closeDetail();
    },
    [closeDetail],
  );

  const submitModel = useCallback(
    async (payload: ModelUpsertPayload, id?: string) => {
      if (!modelProviderId || !id) return;
      setSavingModel(true);
      try {
        await upsertProviderModel({ providerId: modelProviderId, modelId: id, values: payload });
        showToast.success('Model updated');
        setModelEditOpen(false);
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingModel(false);
      }
    },
    [modelProviderId, upsertProviderModel, refresh],
  );

  const openAddModel = useCallback(async () => {
    setAddModelOpen(true);
    try {
      const providers = await listProviderCatalog();
      setProviderOptions(providers.map((p) => ({ id: p.id, display_name: p.display_name })));
    } catch (err) {
      handleApiError(err);
    }
  }, []);

  const submitNewModel = useCallback(
    async (payload: ModelUpsertPayload, _id?: string, providerId?: string) => {
      if (!providerId) return;
      setSavingNewModel(true);
      try {
        await upsertProviderModel({ providerId, values: payload });
        showToast.success('Model created');
        setAddModelOpen(false);
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingNewModel(false);
      }
    },
    [upsertProviderModel, refresh],
  );

  const deleteModel = useCallback(
    (m: ModelRow) => {
      setDeleteModelTarget(m);
      closeDetail();
    },
    [closeDetail],
  );

  const confirmDeleteModel = useCallback(async () => {
    if (!deleteModelTarget) return;
    setDeletingModel(true);
    try {
      await deleteProviderModel({
        providerId: deleteModelTarget.provider.id,
        modelId: deleteModelTarget.id,
      });
      showToast.success('Model deleted');
      setDeleteModelTarget(null);
      refresh();
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeletingModel(false);
    }
  }, [deleteModelTarget, deleteProviderModel, refresh]);

  // ── provider ─────────────────────────────────────────────────────────────
  const editProvider = useCallback(
    async (m: ModelRow) => {
      setEditingProvider(null);
      setProviderEditOpen(true);
      setProviderEditLoading(true);
      closeDetail();
      try {
        const provider = await getModelProvider(m.provider.id);
        setEditingProvider(provider);
      } catch (err) {
        setProviderEditOpen(false);
        handleApiError(err);
      } finally {
        setProviderEditLoading(false);
      }
    },
    [closeDetail],
  );

  const submitProvider = useCallback(
    async (providerId: string, payload: Partial<ModelProviderUpsertPayload>) => {
      setSavingProvider(true);
      try {
        await upsertModelProvider({
          providerId,
          values: payload as ModelProviderUpsertPayload,
        });
        showToast.success('Provider updated');
        setProviderEditOpen(false);
        setEditingProvider(null);
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingProvider(false);
      }
    },
    [upsertModelProvider, refresh],
  );

  // ── API key ────────────────────────────────────────────────────────────
  const editApiKey = useCallback(
    async (m: ModelRow) => {
      if (!m.api_key) return;
      setEditingKey(null);
      setKeyEditOpen(true);
      setKeyEditLoading(true);
      closeDetail();
      try {
        const service = await fetchService(m.api_key.id);
        setEditingKey(service);
      } catch (err) {
        setKeyEditOpen(false);
        handleApiError(err);
      } finally {
        setKeyEditLoading(false);
      }
    },
    [closeDetail, fetchService],
  );

  const submitKey = useCallback(
    async (payload: Partial<ServiceUpsertPayload>, id: string) => {
      setSavingKey(true);
      try {
        await upsertService({ id, values: payload as ServiceUpsertPayload });
        showToast.success('API key updated');
        setKeyEditOpen(false);
        setEditingKey(null);
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingKey(false);
      }
    },
    [upsertService, refresh],
  );

  const deleteApiKey = useCallback(
    (m: ModelRow) => {
      if (!m.api_key) return;
      setDeleteKeyTarget({
        id: m.api_key.id,
        label: m.api_key.label,
        provider: m.provider.display_name,
      });
      closeDetail();
    },
    [closeDetail],
  );

  const confirmDeleteKey = useCallback(async () => {
    if (!deleteKeyTarget) return;
    setDeletingKey(true);
    try {
      await deleteService(deleteKeyTarget.id);
      showToast.success('API key deleted');
      setDeleteKeyTarget(null);
      refresh();
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeletingKey(false);
    }
  }, [deleteKeyTarget, deleteService, refresh]);

  return {
    // detail-drawer action callbacks
    editModel,
    deleteModel,
    editProvider,
    editApiKey,
    deleteApiKey,
    // model editor
    modelEditOpen,
    editingModel,
    savingModel,
    closeModelEdit: useCallback(() => setModelEditOpen(false), []),
    submitModel,
    // model creator
    addModelOpen,
    providerOptions,
    savingNewModel,
    openAddModel,
    closeAddModel: useCallback(() => setAddModelOpen(false), []),
    submitNewModel,
    // provider editor
    providerEditOpen,
    editingProvider,
    providerEditLoading,
    savingProvider,
    closeProviderEdit: useCallback(() => setProviderEditOpen(false), []),
    submitProvider,
    // api-key editor
    keyEditOpen,
    editingKey,
    keyEditLoading,
    savingKey,
    closeKeyEdit: useCallback(() => setKeyEditOpen(false), []),
    submitKey,
    // delete confirmations
    deleteModelTarget,
    deletingModel,
    closeDeleteModel: useCallback(() => setDeleteModelTarget(null), []),
    confirmDeleteModel,
    deleteKeyTarget,
    deletingKey,
    closeDeleteKey: useCallback(() => setDeleteKeyTarget(null), []),
    confirmDeleteKey,
  };
}

export type ModelActions = ReturnType<typeof useModelActions>;

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
import {
  getModelProvider,
  listCloudProviders,
  listProviderCatalog,
} from '@/services/servicesService';
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
  /** Reopen the row-detail drawer — returns from an edit drawer to the detail
   * view it was launched from (breadcrumb / cancel / save). */
  openDetail: (m: ModelRow) => void;
}

/**
 * Orchestrates the edit/delete flows launched from the model-row detail drawer,
 * reusing the existing ModelForm / ModelProviderEdit / ApiKeyEdit drawers and
 * the shared service atoms. Keeps ModelsTablePage thin: the page renders the
 * drawers from this state; all side effects live here.
 */
export function useModelActions({ refresh, closeDetail, openDetail }: UseModelActionsArgs) {
  const [, upsertProviderModel] = useAtom(upsertProviderModelAtom);
  const [, deleteProviderModel] = useAtom(deleteProviderModelAtom);
  const [, upsertModelProvider] = useAtom(upsertModelProviderAtom);
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, deleteService] = useAtom(deleteServiceAtom);
  const [, fetchService] = useAtom(fetchServiceAtom);

  // The row-detail drawer's model that an edit was launched from. Kept so the
  // edit drawers can navigate back to that detail view (breadcrumb / cancel /
  // save) instead of stranding the user on the table.
  const [detailModel, setDetailModel] = useState<ModelRow | null>(null);

  // Return from an edit drawer to the detail view it came from. Pass the
  // (optionally updated) row so the reopened detail reflects the latest values.
  const backToDetail = useCallback(
    (model?: ModelRow) => {
      const target = model ?? detailModel;
      if (target) openDetail(target);
    },
    [detailModel, openDetail],
  );

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

  // Cloud providers for the model form's "Cloud provider" select (both flows).
  const [cloudProviderOptions, setCloudProviderOptions] = useState<
    { id: string; display_name: string }[]
  >([]);
  const loadCloudProviders = useCallback(async () => {
    try {
      const { rows } = await listCloudProviders({ is_active: true, page_size: 100 });
      setCloudProviderOptions(rows.map((c) => ({ id: c.id, display_name: c.display_name })));
    } catch (err) {
      handleApiError(err);
    }
  }, []);

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
      setDetailModel(m);
      setModelProviderId(m.provider.id);
      setEditingModel(m);
      setModelEditOpen(true);
      loadCloudProviders();
      closeDetail();
    },
    [closeDetail, loadCloudProviders],
  );

  const submitModel = useCallback(
    async (payload: ModelUpsertPayload, id?: string) => {
      if (!modelProviderId || !id) return;
      setSavingModel(true);
      try {
        await upsertProviderModel({ providerId: modelProviderId, modelId: id, values: payload });
        showToast.success('Model updated');
        setModelEditOpen(false);
        // Return to the detail view with the edited values merged in so it
        // reflects the save without waiting on a re-fetch.
        if (detailModel) {
          backToDetail({
            ...detailModel,
            name: payload.name,
            display_name: payload.display_name ?? null,
            kind: payload.kind,
            cloud_provider_id: payload.cloud_provider_id ?? null,
            description: payload.description ?? null,
            base_url: payload.base_url ?? null,
            is_active: payload.is_active ?? detailModel.is_active,
          });
        }
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingModel(false);
      }
    },
    [modelProviderId, upsertProviderModel, refresh, detailModel, backToDetail],
  );

  const openAddModel = useCallback(async () => {
    setAddModelOpen(true);
    loadCloudProviders();
    try {
      const providers = await listProviderCatalog();
      setProviderOptions(providers.map((p) => ({ id: p.id, display_name: p.display_name })));
    } catch (err) {
      handleApiError(err);
    }
  }, [loadCloudProviders]);

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
      setDetailModel(m);
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
        // Return to the detail view with the edited provider name merged in.
        if (detailModel) {
          backToDetail({
            ...detailModel,
            provider: {
              ...detailModel.provider,
              display_name: payload.display_name ?? detailModel.provider.display_name,
            },
          });
        }
        refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setSavingProvider(false);
      }
    },
    [upsertModelProvider, refresh, detailModel, backToDetail],
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
    // the model an edit was launched from (drives the edit-drawer breadcrumb)
    detailModel,
    // model editor
    modelEditOpen,
    editingModel,
    savingModel,
    closeModelEdit: useCallback(() => {
      setModelEditOpen(false);
      backToDetail();
    }, [backToDetail]),
    submitModel,
    // model creator
    addModelOpen,
    providerOptions,
    cloudProviderOptions,
    savingNewModel,
    openAddModel,
    closeAddModel: useCallback(() => setAddModelOpen(false), []),
    submitNewModel,
    // provider editor
    providerEditOpen,
    editingProvider,
    providerEditLoading,
    savingProvider,
    closeProviderEdit: useCallback(() => {
      setProviderEditOpen(false);
      backToDetail();
    }, [backToDetail]),
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

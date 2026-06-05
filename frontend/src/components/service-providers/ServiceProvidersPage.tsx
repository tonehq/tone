'use client';

import { useAtom } from 'jotai';
import { Plug, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import servicesAtom, {
  deleteProviderAtom,
  fetchServiceAtom,
  fetchServicesAtom,
  upsertServiceAtom,
} from '@/atoms/ServicesAtom';
import { CustomButton, CustomModal, SearchBar, SelectInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listProviderKeys } from '@/services/servicesService';
import type { ProviderUsage, Service, ServiceKind, ServiceUpsertPayload } from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ApiKeyCreateDrawer from './api-key-create-drawer';
import ApiKeyEditDrawer from './api-key-edit-drawer';
import ServiceGrid from './service-grid';
import ServiceGridSkeleton from './service-grid-skeleton';

const PAGE_SIZE = 12;

const TYPE_FILTER_OPTIONS = [
  { value: 'all', label: 'All types' },
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'STT' },
  { value: 'tts', label: 'TTS' },
];

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [state] = useAtom(servicesAtom);
  const [, fetchServices] = useAtom(fetchServicesAtom);
  const [, fetchService] = useAtom(fetchServiceAtom);
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, deleteProvider] = useAtom(deleteProviderAtom);

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | ServiceKind>('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProviderUsage | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const pageRef = useRef(state.page);
  pageRef.current = state.page;

  const loadInitial = useCallback(
    (overrides?: { search?: string; service_type?: 'all' | ServiceKind }) =>
      fetchServices({
        page: 1,
        page_size: PAGE_SIZE,
        search: overrides?.search ?? search ?? undefined,
        service_type: overrides?.service_type ?? typeFilter,
        append: false,
      }),
    [fetchServices, search, typeFilter],
  );

  const hasFetchedRef = useRef(false);
  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    loadInitial().catch(handleApiError);
  }, [loadInitial]);

  const handleSearch = useCallback(
    (value: string) => {
      setSearch(value);
      loadInitial({ search: value }).catch(handleApiError);
    },
    [loadInitial],
  );

  const handleTypeFilter = useCallback(
    (value: string) => {
      const v = value as 'all' | ServiceKind;
      setTypeFilter(v);
      loadInitial({ service_type: v }).catch(handleApiError);
    },
    [loadInitial],
  );

  const hasNextPage = useMemo(
    () => state.items.length < state.total,
    [state.items.length, state.total],
  );

  const handleFetchNext = useCallback(() => {
    if (state.loadingMore) return;
    fetchServices({
      page: pageRef.current + 1,
      page_size: PAGE_SIZE,
      search: search || undefined,
      service_type: typeFilter,
      append: true,
    }).catch(handleApiError);
  }, [fetchServices, search, typeFilter, state.loadingMore]);

  const handleSelect = useCallback(
    (u: ProviderUsage) => {
      router.push(`/settings/model-providers/${u.provider.id}/${u.service_type}`);
    },
    [router],
  );

  const handleAdd = useCallback(() => {
    setCreateOpen(true);
  }, []);

  const handleEdit = useCallback(
    async (u: ProviderUsage) => {
      // Open the drawer immediately with a loader, then resolve the key.
      // Prefer the default key for this (provider, kind); fall back to the
      // most recently updated key of that kind so the pencil always opens an
      // editor instead of bouncing the user to the detail page.
      setEditingService(null);
      setEditOpen(true);
      setEditLoading(true);
      try {
        let keyId = u.default_api_key?.id;
        if (!keyId) {
          const { rows } = await listProviderKeys(u.provider.id, {
            page: 1,
            page_size: 1,
            service_type: u.service_type,
            sort_by: '-updated_at',
          });
          keyId = rows[0]?.id;
        }
        if (!keyId) {
          setEditOpen(false);
          router.push(`/settings/model-providers/${u.provider.id}/${u.service_type}`);
          return;
        }
        const svc = await fetchService(keyId);
        setEditingService(svc);
      } catch (err) {
        setEditOpen(false);
        handleApiError(err);
      } finally {
        setEditLoading(false);
      }
    },
    [fetchService, router],
  );

  const handleEditClose = useCallback(() => {
    setEditOpen(false);
    setEditingService(null);
  }, []);

  const handleDeleteRequest = useCallback((u: ProviderUsage) => {
    setDeleteTarget(u);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      const { deleted } = await deleteProvider({
        providerId: deleteTarget.provider.id,
        serviceType: deleteTarget.service_type,
      });
      // Keep the modal open with the Delete button still in its loading state
      // until the listing refresh lands, so the user doesn't see a stale card
      // briefly remain after dismissing the dialog.
      await loadInitial();
      const typeLabel = deleteTarget.service_type.toUpperCase();
      showToast.success(
        `Removed ${deleted} key${deleted === 1 ? '' : 's'}`,
        `${deleteTarget.provider.display_name} · ${typeLabel} keys have been deleted.`,
      );
      setDeleteTarget(null);
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsDeleting(false);
    }
  }, [deleteTarget, deleteProvider, loadInitial]);

  const handleCreate = useCallback(
    async (payload: ServiceUpsertPayload) => {
      setIsSaving(true);
      try {
        await upsertService({ values: payload });
        // Wait for the listing refresh before dismissing the drawer so the
        // Create button keeps its loading state until the new card is in view.
        await loadInitial();
        showToast.success('Provider added');
        setCreateOpen(false);
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, loadInitial],
  );

  const handleUpdate = useCallback(
    async (payload: Partial<ServiceUpsertPayload>, id: string) => {
      setIsSaving(true);
      try {
        await upsertService({ id, values: payload as ServiceUpsertPayload });
        // Mirror handleCreate / handleDeleteConfirm: keep the Save button in
        // its loading state until the refreshed list lands.
        await loadInitial();
        showToast.success('Provider updated');
        setEditOpen(false);
        setEditingService(null);
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, loadInitial],
  );

  const isInitialLoading = state.loading && state.items.length === 0;
  const isEmpty = !isInitialLoading && state.items.length === 0;
  const hasActiveFilter = !!search || typeFilter !== 'all';

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Model Providers
            </h1>
            {state.total > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {state.total}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect LLM, STT, and TTS providers with API keys.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={handleAdd}>
          Add Provider
        </CustomButton>
      </div>

      {/* toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search providers or services…"
          value={search}
          onSearch={handleSearch}
          debounceMs={300}
          containerClassName="max-w-xs flex-1"
        />
        <SelectInput
          name="type-filter"
          options={TYPE_FILTER_OPTIONS}
          value={typeFilter}
          onValueChange={handleTypeFilter}
          placeholder="All types"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
      </div>

      {/* grid */}
      <div className="flex min-h-0 flex-1 flex-col">
        {isInitialLoading ? (
          <ServiceGridSkeleton count={6} />
        ) : isEmpty ? (
          <EmptyState onAdd={handleAdd} hasFilter={hasActiveFilter} />
        ) : (
          <ServiceGrid
            items={state.items}
            total={state.total}
            hasNextPage={hasNextPage}
            isFetchingNextPage={state.loadingMore}
            fetchNextPage={handleFetchNext}
            onSelect={handleSelect}
            onEdit={handleEdit}
            onDelete={handleDeleteRequest}
          />
        )}
      </div>

      {/* create drawer */}
      <ApiKeyCreateDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        isPending={isSaving}
      />

      {/* edit drawer — opened from the listing where each card is a provider
          connection, so the copy mirrors the "Add provider" button. */}
      <ApiKeyEditDrawer
        open={editOpen}
        editing={editingService}
        loading={editLoading}
        title="Edit provider"
        description="Update this provider connection. To rotate the secret, delete this key and add a new one."
        onClose={handleEditClose}
        onSubmit={handleUpdate}
        isPending={isSaving}
      />

      {/* delete confirmation */}
      <CustomModal
        open={!!deleteTarget}
        onClose={() => !isDeleting && setDeleteTarget(null)}
        title="Delete provider keys?"
        description={
          deleteTarget
            ? `This will permanently delete ${deleteTarget.api_key_count} ${deleteTarget.service_type.toUpperCase()} key${
                deleteTarget.api_key_count === 1 ? '' : 's'
              } for ${deleteTarget.provider.display_name}. Agents using these credentials will stop working.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  );
}

function EmptyState({ onAdd, hasFilter }: { onAdd: () => void; hasFilter: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 py-12">
      <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
        <Plug className="size-6 text-muted-foreground" />
      </div>
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No matching providers' : 'No providers yet'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or type filter.'
            : 'Add a provider with an API key so your agents can use it.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={onAdd}>
          Add Provider
        </CustomButton>
      )}
    </div>
  );
}

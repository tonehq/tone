'use client';

import { useAtom } from 'jotai';
import { Plug, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';

import { deleteProviderAtom, fetchServiceAtom, upsertServiceAtom } from '@/atoms/ServicesAtom';
import {
  CustomButton,
  CustomModal,
  FacetFilterBar,
  FacetFilterDrawer,
  useFacetedList,
} from '@/components/shared';
import { servicesListConfig } from '@/components/service-providers/servicesListConfig';
import { Badge } from '@/components/ui/badge';
import { listProviderKeys } from '@/services/servicesService';
import type { ProviderUsage, Service, ServiceUpsertPayload } from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ApiKeyCreateDrawer from './api-key-create-drawer';
import ApiKeyEditDrawer from './api-key-edit-drawer';
import ServiceGrid from './service-grid';
import ServiceGridSkeleton from './service-grid-skeleton';

const noop = () => {};

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [, fetchService] = useAtom(fetchServiceAtom);
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, deleteProvider] = useAtom(deleteProviderAtom);

  const fl = useFacetedList(servicesListConfig);

  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProviderUsage | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
      const typeLabel = deleteTarget.service_type.toUpperCase();
      showToast.success(
        `Removed ${deleted} key${deleted === 1 ? '' : 's'}`,
        `${deleteTarget.provider.display_name} · ${typeLabel} keys have been deleted.`,
      );
      setDeleteTarget(null);
      fl.refresh();
    } catch (err) {
      handleApiError(err);
    } finally {
      setIsDeleting(false);
    }
  }, [deleteTarget, deleteProvider, fl]);

  const handleCreate = useCallback(
    async (payload: ServiceUpsertPayload) => {
      setIsSaving(true);
      try {
        await upsertService({ values: payload });
        showToast.success('Provider added');
        setCreateOpen(false);
        fl.refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, fl],
  );

  const handleUpdate = useCallback(
    async (payload: Partial<ServiceUpsertPayload>, id: string) => {
      setIsSaving(true);
      try {
        await upsertService({ id, values: payload as ServiceUpsertPayload });
        showToast.success('Provider updated');
        setEditOpen(false);
        setEditingService(null);
        fl.refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, fl],
  );

  const isInitialLoading = fl.listLoading && fl.rows.length === 0;
  const isEmpty = !isInitialLoading && fl.rows.length === 0;
  const hasActiveFilter = fl.hasActiveFilters;

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Model Providers
            </h1>
            {fl.total > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {fl.total}
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
      <FacetFilterBar
        fields={fl.tokenFields}
        tokens={fl.tokens}
        onTokensChange={fl.setTokens}
        onClear={fl.clearAll}
        showClear={fl.hasActiveFilters}
        placeholder="Search providers… (e.g. name:OpenAI, type:llm)"
        drawerFilterCount={fl.drawerFilterCount}
        onOpenDrawer={() => setFilterDrawerOpen(true)}
      />

      {/* grid */}
      <div className="flex min-h-0 flex-1 flex-col">
        {isInitialLoading ? (
          <ServiceGridSkeleton count={6} />
        ) : isEmpty ? (
          <EmptyState onAdd={handleAdd} hasFilter={hasActiveFilter} />
        ) : (
          <ServiceGrid
            items={fl.rows}
            total={fl.total}
            hasNextPage={false}
            isFetchingNextPage={false}
            fetchNextPage={noop}
            onSelect={handleSelect}
            onEdit={handleEdit}
            onDelete={handleDeleteRequest}
          />
        )}
      </div>

      {/* filter drawer */}
      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter providers by type."
        sections={servicesListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />

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

'use client';

import { useAtom } from 'jotai';
import { Plug, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';

import {
  deleteProviderAtom,
  upsertModelProviderAtom,
  upsertServiceAtom,
} from '@/atoms/ServicesAtom';
import {
  CustomButton,
  CustomModal,
  FacetFilterBar,
  FacetFilterDrawer,
  IconChip,
  useFacetedList,
} from '@/components/shared';
import { servicesListConfig } from '@/components/service-providers/servicesListConfig';
import { Badge } from '@/components/ui/badge';
import { getModelProvider } from '@/services/servicesService';
import type {
  ModelProvider,
  ModelProviderUpsertPayload,
  ProviderUsage,
  ServiceUpsertPayload,
} from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ApiKeyCreateDrawer from './api-key-create-drawer';
import ModelProviderEditDrawer from './model-provider-edit-drawer';
import ServiceGrid from './service-grid';
import ServiceGridSkeleton from './service-grid-skeleton';

const noop = () => {};

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, upsertModelProvider] = useAtom(upsertModelProviderAtom);
  const [, deleteProvider] = useAtom(deleteProviderAtom);

  const fl = useFacetedList(servicesListConfig);

  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ModelProvider | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProviderUsage | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSelect = useCallback(
    (u: ProviderUsage) => {
      // Unconnected cards route to the provider-level detail page (no kind
      // suffix) since there's no service_type context yet — the user picks a
      // kind + adds a key there.
      const target = u.service_type
        ? `/settings/model-providers/${u.provider.id}/${u.service_type}`
        : `/settings/model-providers/${u.provider.id}`;
      router.push(target);
    },
    [router],
  );

  const handleAdd = useCallback(() => {
    setCreateOpen(true);
  }, []);

  const handleEdit = useCallback(async (u: ProviderUsage) => {
    // The listing edit is provider-scoped — API keys and models are edited
    // from the provider detail page. Open the drawer immediately with a
    // loader while we fetch the full ModelProvider row (the card only has
    // slug/display_name/description; the drawer also needs website_url and
    // is_active).
    setEditingProvider(null);
    setEditOpen(true);
    setEditLoading(true);
    try {
      const provider = await getModelProvider(u.provider.id);
      setEditingProvider(provider);
    } catch (err) {
      setEditOpen(false);
      handleApiError(err);
    } finally {
      setEditLoading(false);
    }
  }, []);

  const handleEditClose = useCallback(() => {
    setEditOpen(false);
    setEditingProvider(null);
  }, []);

  const handleDeleteRequest = useCallback((u: ProviderUsage) => {
    setDeleteTarget(u);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget || !deleteTarget.service_type) return;
    const serviceType = deleteTarget.service_type;
    setIsDeleting(true);
    try {
      const { deleted } = await deleteProvider({
        providerId: deleteTarget.provider.id,
        serviceType,
      });
      const typeLabel = serviceType.toUpperCase();
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

  const handleUpdateProvider = useCallback(
    async (providerId: string, payload: Partial<ModelProviderUpsertPayload>) => {
      setIsSaving(true);
      try {
        await upsertModelProvider({
          providerId,
          values: payload as ModelProviderUpsertPayload,
        });
        showToast.success('Provider updated');
        setEditOpen(false);
        setEditingProvider(null);
        fl.refresh();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertModelProvider, fl],
  );

  // Passed to ApiKeyCreateDrawer's "+ Create new provider" inline flow. The
  // drawer creates the ModelProvider via this callback, then uses the returned
  // id to create the ApiKey in the same submit gesture. Refresh here so the
  // "provider only" path (no API key) still updates the grid — that branch
  // short-circuits inside the drawer and never calls ``onSubmit``.
  const handleInlineCreateProvider = useCallback(
    async (payload: ModelProviderUpsertPayload): Promise<ModelProvider> => {
      const created = await upsertModelProvider({ values: payload });
      fl.refresh();
      return created;
    },
    [upsertModelProvider, fl],
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
            <h1 className="font-display text-[1.75rem] font-semibold tracking-[-0.03em] text-foreground">
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

      {/* create drawer — pick from the catalog, or use the inline
          "+ Create new provider" toggle to define a brand-new one in the
          same submit. */}
      <ApiKeyCreateDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        onCreateProvider={handleInlineCreateProvider}
        isPending={isSaving}
      />

      {/* edit drawer — provider-scoped only. API keys and models are edited
          from the provider detail page (each has its own flow). */}
      <ModelProviderEditDrawer
        open={editOpen}
        editing={editingProvider}
        loading={editLoading}
        onClose={handleEditClose}
        onSubmit={handleUpdateProvider}
        isPending={isSaving}
      />

      {/* delete confirmation */}
      <CustomModal
        open={!!deleteTarget}
        onClose={() => !isDeleting && setDeleteTarget(null)}
        title="Delete provider keys?"
        description={
          deleteTarget
            ? `This will permanently delete ${deleteTarget.api_key_count} ${(
                deleteTarget.service_type ?? ''
              ).toUpperCase()} key${
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
      <IconChip icon={<Plug strokeWidth={1.75} />} tone="muted" size="xl" />
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

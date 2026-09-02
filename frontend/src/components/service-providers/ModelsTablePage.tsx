'use client';

import { useAtom } from 'jotai';
import { Plus } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';

import { upsertModelProviderAtom, upsertServiceAtom } from '@/atoms/ServicesAtom';
import {
  CustomButton,
  CustomTable,
  FacetFilterBar,
  FacetFilterDrawer,
  useFacetedList,
} from '@/components/shared';
import { modelsListConfig } from '@/components/service-providers/modelsListConfig';
import { Badge } from '@/components/ui/badge';
import type {
  ModelProvider,
  ModelProviderUpsertPayload,
  ModelRow,
  ServiceUpsertPayload,
} from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ApiKeyCreateDrawer from './api-key-create-drawer';
import { getModelColumns } from './modelTableColumns';
import ModelDetailDrawer from './ModelDetailDrawer';

export default function ModelsTablePage() {
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, upsertModelProvider] = useAtom(upsertModelProviderAtom);

  const fl = useFacetedList(modelsListConfig);
  const columns = useMemo(() => getModelColumns(), []);

  const [selected, setSelected] = useState<ModelRow | null>(null);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

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

  const handleInlineCreateProvider = useCallback(
    async (payload: ModelProviderUpsertPayload): Promise<ModelProvider> => {
      const created = await upsertModelProvider({ values: payload });
      fl.refresh();
      return created;
    },
    [upsertModelProvider, fl],
  );

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
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
            Every model across your providers, with the API key configured for each.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus className="size-4" />}
          onClick={() => setCreateOpen(true)}
        >
          Add Provider
        </CustomButton>
      </div>

      <FacetFilterBar
        fields={fl.tokenFields}
        tokens={fl.tokens}
        onTokensChange={fl.setTokens}
        onClear={fl.clearAll}
        showClear={fl.hasActiveFilters}
        placeholder="Search models… (e.g. name:gpt-4o, provider:OpenAI, type:llm)"
        drawerFilterCount={fl.drawerFilterCount}
        onOpenDrawer={() => setFilterDrawerOpen(true)}
      />

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={fl.rows}
          rowKey="id"
          loading={fl.listLoading}
          onRowClick={(m) => setSelected(m)}
          onSortChange={fl.handleSortChange}
          initialSort={{ field: 'name', order: 'asc' }}
          pagination={{
            current: fl.page,
            pageSize: fl.pageSize,
            total: fl.total,
            pageSizeOptions: fl.pageSizeOptions,
            onChange: fl.handlePaginationChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-2 py-12 text-center">
              <p className="text-sm font-medium text-foreground">
                {fl.hasActiveFilters ? 'No matching models' : 'No models yet'}
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                {fl.hasActiveFilters
                  ? 'Try clearing the search or filters.'
                  : 'Add a provider with an API key so your agents can use its models.'}
              </p>
            </div>
          }
        />
      </div>

      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter models by provider and type."
        sections={modelsListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />

      <ApiKeyCreateDrawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        onCreateProvider={handleInlineCreateProvider}
        isPending={isSaving}
      />

      <ModelDetailDrawer model={selected} open={!!selected} onClose={() => setSelected(null)} />
    </div>
  );
}

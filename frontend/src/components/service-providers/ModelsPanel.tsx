'use client';

import {
  deleteModelAtom,
  fetchModelsAtom,
  modelsAtom,
  upsertModelAtom,
} from '@/atoms/ProviderAtom';
import ModelUpsertModal from '@/components/service-providers/ModelUpsertModal';
import { ActionMenu, CustomButton, CustomTable } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn } from '@/types/components';
import type { ModelUpsertPayload, ServiceProvider, ServiceProviderModel } from '@/types/provider';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Box, BrainCircuit, ChevronLeft, Key, Plus, Search, Server } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { MODELS_PAGE_SIZE, TYPE_BADGE_STYLES, TYPE_ICON_STYLES, TYPE_ICONS } from './constants';

interface ModelsPanelProps {
  selectedProvider: ServiceProvider | null;
  onBack: () => void;
}

export default function ModelsPanel({ selectedProvider, onBack }: ModelsPanelProps) {
  const [modelsState] = useAtom(modelsAtom);
  const [, fetchModels] = useAtom(fetchModelsAtom);
  const [, upsertModel] = useAtom(upsertModelAtom);
  const [, removeModel] = useAtom(deleteModelAtom);

  const [modelPage, setModelPage] = useState(1);
  const [modelPageSize, setModelPageSize] = useState(MODELS_PAGE_SIZE);
  const [modelSearch, setModelSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ServiceProviderModel | null>(null);

  // ── Reset state when provider changes ────────────────────────────

  const prevProviderIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!selectedProvider) return;
    if (prevProviderIdRef.current === selectedProvider.id) return;
    prevProviderIdRef.current = selectedProvider.id;
    setModelPage(1);
    setModelSearch('');
    fetchModels({
      service_provider_id: selectedProvider.id,
      page: 1,
      page_size: modelPageSize,
    }).catch(handleApiError);
  }, [selectedProvider, fetchModels, modelPageSize]);

  // ── Params helper ────────────────────────────────────────────────

  const buildModelParams = useCallback(
    (page: number, pageSize: number, nameOverride?: string) => {
      if (!selectedProvider) return null;
      const params: {
        service_provider_id: number;
        page: number;
        page_size: number;
        name?: string;
      } = {
        service_provider_id: selectedProvider.id,
        page,
        page_size: pageSize,
      };
      const name = nameOverride ?? modelSearch;
      if (name.trim()) params.name = name.trim();
      return params;
    },
    [selectedProvider, modelSearch],
  );

  // ── Debounced search ─────────────────────────────────────────────

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedSearch = useMemo(
    () => (query: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        const params = buildModelParams(1, modelPageSize, query);
        if (params) {
          setModelPage(1);
          fetchModels(params).catch(handleApiError);
        }
      }, 300);
    },
    [fetchModels, buildModelParams, modelPageSize],
  );

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    },
    [],
  );

  // ── Pagination ───────────────────────────────────────────────────

  const handlePageChange = useCallback(
    (page: number, pageSize: number) => {
      setModelPage(page);
      setModelPageSize(pageSize);
      const params = buildModelParams(page, pageSize);
      if (params) fetchModels(params).catch(handleApiError);
    },
    [fetchModels, buildModelParams],
  );

  // ── CRUD ─────────────────────────────────────────────────────────

  const handleSubmit = useCallback(
    async (payload: ModelUpsertPayload) => {
      try {
        await upsertModel(payload);
        showToast.success(payload.id ? 'Model updated' : 'Model created');
        const params = buildModelParams(modelPage, modelPageSize);
        if (params) await fetchModels(params);
      } catch (error) {
        handleApiError(error);
        throw error;
      }
    },
    [upsertModel, fetchModels, buildModelParams, modelPage, modelPageSize],
  );

  const handleDelete = useCallback(
    async (modelId: number) => {
      try {
        await removeModel(modelId);
        showToast.success('Model deleted');
        const params = buildModelParams(modelPage, modelPageSize);
        if (params) await fetchModels(params);
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeModel, fetchModels, buildModelParams, modelPage, modelPageSize],
  );

  const openEdit = useCallback((model: ServiceProviderModel) => {
    setEditingModel(model);
    setModalOpen(true);
  }, []);

  const openCreate = useCallback(() => {
    setEditingModel(null);
    setModalOpen(true);
  }, []);

  // ── Columns ──────────────────────────────────────────────────────

  const providerType = selectedProvider?.provider_type ?? '';

  const columns: CustomTableColumn<ServiceProviderModel>[] = [
    {
      key: 'name',
      title: 'Model',
      dataIndex: 'name',
      sorter: true,
      render: (_value, record) => (
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              'flex size-7 shrink-0 items-center justify-center rounded-md',
              TYPE_ICON_STYLES[providerType] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {TYPE_ICONS[providerType] ?? <Box className="size-3.5" />}
          </div>
          <div className="flex flex-col">
            <span className="font-medium text-foreground">{record.name}</span>
            {record.meta_data?.model && record.meta_data.model !== record.name && (
              <span className="text-[11px] text-muted-foreground">
                {String(record.meta_data.model)}
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'meta_data',
      title: 'Metadata',
      render: (_value, record) => {
        if (!record.meta_data || Object.keys(record.meta_data).length === 0) {
          return <span className="text-muted-foreground">—</span>;
        }
        const entries = Object.entries(record.meta_data);
        return (
          <div className="flex flex-wrap gap-1">
            {entries.slice(0, 3).map(([k, v]) => (
              <span
                key={k}
                className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                {k}: {String(v)}
              </span>
            ))}
            {entries.length > 3 && (
              <span className="text-[10px] text-muted-foreground">+{entries.length - 3} more</span>
            )}
          </div>
        );
      },
    },
    {
      key: 'updated_at',
      title: 'Updated',
      dataIndex: 'updated_at',
      sorter: true,
      render: (value) =>
        value ? (
          <span className="text-sm text-muted-foreground">
            {formatDate(value as number, 'DD MMM YYYY')}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      render: (_value, record) => (
        <ActionMenu
          onEdit={() => openEdit(record)}
          onDelete={() => handleDelete(record.id)}
          itemName={record.name}
        />
      ),
    },
  ];

  // ── Render ───────────────────────────────────────────────────────

  if (!selectedProvider) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <div className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5">
          <BrainCircuit className="size-7 text-primary/60" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-foreground">Select a provider</p>
          <p className="mt-1 max-w-[240px] text-xs leading-relaxed text-muted-foreground">
            Choose a service provider from the list to view and manage its models
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden"
            aria-label="Back to providers"
          >
            <ChevronLeft className="size-5" />
          </button>
          <div
            className={cn(
              'flex size-9 items-center justify-center rounded-lg',
              TYPE_ICON_STYLES[selectedProvider.provider_type] ?? 'bg-muted',
            )}
          >
            {TYPE_ICONS[selectedProvider.provider_type] ?? <Server className="size-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-foreground">
                {selectedProvider.display_name}
              </h2>
              <Badge
                className={cn(
                  'text-[10px] font-semibold uppercase tracking-wide',
                  TYPE_BADGE_STYLES[selectedProvider.provider_type],
                )}
              >
                {selectedProvider.provider_type}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>
                {modelsState.pagination?.total ?? modelsState.models.length} model
                {(modelsState.pagination?.total ?? modelsState.models.length) !== 1 ? 's' : ''}
              </span>
              {selectedProvider.description && (
                <>
                  <span className="text-border">|</span>
                  <span className="truncate">{selectedProvider.description}</span>
                </>
              )}
              {selectedProvider.api_key && (
                <>
                  <span className="text-border">|</span>
                  <span
                    className={cn(
                      'flex items-center gap-0.5',
                      selectedProvider.api_key.is_valid
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-amber-600 dark:text-amber-400',
                    )}
                  >
                    <Key className="size-3" />
                    {selectedProvider.api_key.api_key_hint}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        <CustomButton type="primary" size="sm" icon={<Plus />} onClick={openCreate}>
          Add Model
        </CustomButton>
      </div>

      {/* Search + Table */}
      <div className="flex min-h-0 flex-1 flex-col p-4">
        <div className="relative mb-4 max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search models..."
            value={modelSearch}
            onChange={(e) => {
              setModelSearch(e.target.value);
              debouncedSearch(e.target.value);
            }}
            className="h-9 w-full cursor-text rounded-lg border border-input bg-background pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
          />
        </div>
        <CustomTable
          columns={columns}
          dataSource={modelsState.models}
          rowKey="id"
          loading={modelsState.loading}
          pagination={{
            current: modelPage,
            pageSize: modelPageSize,
            total: modelsState.pagination?.total,
            onChange: handlePageChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-3 py-12">
              <div className="flex size-11 items-center justify-center rounded-xl bg-muted">
                <Box className="size-5 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">No models yet</p>
                <p className="mt-0.5 text-xs text-muted-foreground">Add a model to this provider</p>
              </div>
              <CustomButton type="primary" size="sm" icon={<Plus />} onClick={openCreate}>
                Add Model
              </CustomButton>
            </div>
          }
        />
      </div>

      {/* Modal */}
      <ModelUpsertModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        serviceProviderId={selectedProvider.id}
        defaultServiceType={selectedProvider.provider_type}
        providerApiKeyId={selectedProvider.api_key?.id}
        model={editingModel}
      />
    </>
  );
}

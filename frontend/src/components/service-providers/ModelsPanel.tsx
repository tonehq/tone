'use client';

import {
  deleteModelAtom,
  fetchModelsAtom,
  modelsAtom,
  upsertModelAtom,
} from '@/atoms/ProviderAtom';
import ModelUpsertModal from '@/components/service-providers/ModelUpsertModal';
import ProviderLogo from '@/components/service-providers/ProviderLogo';
import { ActionMenu, CustomButton, CustomTable } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { CustomTableColumn } from '@/types/components';
import type { ModelUpsertPayload, ServiceProvider, ServiceProviderModel } from '@/types/provider';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Box, BrainCircuit, ChevronLeft, Plus, Search } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { MODELS_PAGE_SIZE, TYPE_BADGE_STYLES } from './constants';

interface ModelsPanelProps {
  selectedProvider: ServiceProvider | null;
  onBack: () => void;
  /** Hide the provider header when embedded in tabs */
  compact?: boolean;
}

export default function ModelsPanel({ selectedProvider, onBack, compact }: ModelsPanelProps) {
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
      model_provider_menu_id: selectedProvider.id,
      page: 1,
      page_size: modelPageSize,
    }).catch(handleApiError);
  }, [selectedProvider, fetchModels, modelPageSize]);

  // ── Params helper ────────────────────────────────────────────────

  const buildModelParams = useCallback(
    (page: number, pageSize: number, nameOverride?: string) => {
      if (!selectedProvider) return null;
      const params: {
        model_provider_menu_id: number;
        page: number;
        page_size: number;
        name?: string;
      } = {
        model_provider_menu_id: selectedProvider.id,
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
  const providerName = selectedProvider?.name ?? '';

  const columns: CustomTableColumn<ServiceProviderModel>[] = [
    {
      key: 'name',
      title: 'Model',
      dataIndex: 'name',
      sorter: true,
      render: (_value, record) => (
        <div className="flex items-center gap-2.5">
          <ProviderLogo
            providerName={providerName}
            serviceType={providerType}
            className="size-7 rounded-md"
            imgSize={16}
          />
          <span className="truncate font-medium text-foreground">{record.name}</span>
        </div>
      ),
    },
    {
      key: 'service_type',
      title: 'Type',
      width: '100px',
      render: (_value, record) => {
        const t = record.service_type ?? providerType;
        if (!t) return <span className="text-muted-foreground">—</span>;
        return (
          <Badge
            className={cn(
              'text-[10px] font-semibold uppercase tracking-wide',
              TYPE_BADGE_STYLES[t] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {t}
          </Badge>
        );
      },
    },
    {
      key: 'status',
      title: 'Status',
      width: '110px',
      render: (_value, record) => {
        const s = (record.status ?? 'active').toLowerCase();
        const isActive = s === 'active';
        return (
          <span className="inline-flex items-center gap-1.5 text-xs">
            <span
              className={cn('size-1.5 rounded-full', isActive ? 'bg-emerald-500' : 'bg-amber-500')}
            />
            <span
              className={cn('capitalize', isActive ? 'text-foreground' : 'text-muted-foreground')}
            >
              {s}
            </span>
          </span>
        );
      },
    },
    {
      key: 'meta_data',
      title: 'Metadata',
      render: (_value, record) => {
        const entries = record.meta_data
          ? Object.entries(record.meta_data).filter(([k]) => k !== 'model')
          : [];
        if (entries.length === 0) {
          return <span className="text-xs text-muted-foreground">—</span>;
        }
        const visible = entries.slice(0, 2);
        const overflow = entries.length - visible.length;
        const fullText = entries.map(([k, v]) => `${k}: ${String(v)}`).join('\n');
        return (
          <div className="flex flex-wrap items-center gap-1" title={fullText}>
            {visible.map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                <span className="text-foreground/80">{k}</span>
                <span className="text-border">=</span>
                <span className="truncate max-w-30">{String(v)}</span>
              </span>
            ))}
            {overflow > 0 && (
              <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                +{overflow}
              </span>
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
      width: '130px',
      render: (value) =>
        value ? (
          <span className="text-xs text-muted-foreground">
            {formatDate(value as number, 'DD MMM YYYY')}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      width: '56px',
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
        <div className="flex size-16 items-center justify-center rounded-2xl bg-linear-to-br from-primary/10 to-primary/5">
          <BrainCircuit className="size-7 text-primary/60" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-foreground">Select a provider</p>
          <p className="mt-1 max-w-60 text-xs leading-relaxed text-muted-foreground">
            Choose a service provider from the list to view and manage its models
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header — hidden in compact/tab mode */}
      {!compact && (
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground lg:hidden"
              aria-label="Back to providers"
            >
              <ChevronLeft className="size-5" />
            </button>
            <ProviderLogo
              providerName={selectedProvider.name}
              serviceType={selectedProvider.provider_type}
              className="size-9 rounded-lg"
              imgSize={22}
            />
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
              </div>
            </div>
          </div>
          <CustomButton type="primary" size="sm" icon={<Plus />} onClick={openCreate}>
            Add Model
          </CustomButton>
        </div>
      )}

      {/* Search + Table */}
      <div
        className={cn(
          'flex min-h-0 flex-1 flex-col overflow-hidden',
          compact ? 'px-6 py-4' : 'p-4',
        )}
      >
        <div className="mb-4 flex items-center gap-3">
          <div className="relative max-w-xs flex-1">
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
          {compact && (
            <CustomButton type="primary" size="sm" icon={<Plus />} onClick={openCreate}>
              Add Model
            </CustomButton>
          )}
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

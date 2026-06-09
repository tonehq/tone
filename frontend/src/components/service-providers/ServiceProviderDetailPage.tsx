'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useAtom } from 'jotai';
import { ChevronRight, KeyRound, Layers, Pencil, Plus, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  deleteProviderModelAtom,
  fetchProviderKeysAtom,
  fetchProviderModelsAtom,
  providerKeysAtom,
  providerModelsAtom,
  upsertProviderModelAtom,
  upsertServiceAtom,
} from '@/atoms/ServicesAtom';
import { CustomButton, CustomModal, CustomTable, TokenSearchBar } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import {
  deleteService,
  listProviderCatalog,
  listProviderKeyFilterValues,
  listProviderModelFilterValues,
} from '@/services/servicesService';
import type { ModelUpsertPayload } from '@/services/servicesService';
import type {
  CustomTableColumn,
  CustomTableSortState,
  SearchToken,
  TokenSearchField,
} from '@/types/components';
import type {
  ProviderCatalogItem,
  ProviderModel,
  Service,
  ServiceKind,
  ServiceUpsertPayload,
} from '@/types/service';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ApiKeyCreateDrawer from './api-key-create-drawer';
import ApiKeyEditDrawer from './api-key-edit-drawer';
import ModelFormDrawer from './model-form-drawer';
import ProviderLogo from './ProviderLogo';
import { TYPE_BADGE_STYLES } from './constants';

const KEYS_PAGE_SIZE = 20;
const MODELS_PAGE_SIZE = 20;

export default function ServiceProviderDetailPage() {
  const params = useParams<{ providerId: string; serviceType?: string }>();
  const providerId = params?.providerId;
  // The detail page is scoped to one (provider, service_type). The route is
  // /model-providers/{providerId}/{serviceType}; the older /{providerId} URL
  // now redirects to the listing.
  const rawServiceType = params?.serviceType;
  const serviceType: ServiceKind | null =
    rawServiceType === 'llm' || rawServiceType === 'stt' || rawServiceType === 'tts'
      ? rawServiceType
      : null;

  const [keysState] = useAtom(providerKeysAtom);
  const [modelsState] = useAtom(providerModelsAtom);
  const [, fetchKeys] = useAtom(fetchProviderKeysAtom);
  const [, fetchModels] = useAtom(fetchProviderModelsAtom);
  const [, upsertService] = useAtom(upsertServiceAtom);
  const [, upsertProviderModel] = useAtom(upsertProviderModelAtom);
  const [, deleteProviderModel] = useAtom(deleteProviderModelAtom);

  const [provider, setProvider] = useState<ProviderCatalogItem | null>(null);
  const [providerLoading, setProviderLoading] = useState(true);

  // ─── keys panel local state ───────────────────────────────────────────────
  const [keysSearch, setKeysSearch] = useState('');
  const [keysPage, setKeysPage] = useState(1);
  const [keysSort, setKeysSort] = useState('-updated_at');

  // ─── models panel local state ─────────────────────────────────────────────
  const [modelsSearch, setModelsSearch] = useState('');
  const [modelsPage, setModelsPage] = useState(1);
  const [modelsSort, setModelsSort] = useState('name');

  // ─── drawer + delete modal state ──────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Service | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Service | null>(null);
  const [deleting, setDeleting] = useState(false);

  // ─── model drawer + delete modal state ────────────────────────────────────
  const [modelDrawerOpen, setModelDrawerOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ProviderModel | null>(null);
  const [isSavingModel, setIsSavingModel] = useState(false);
  const [modelDeleteTarget, setModelDeleteTarget] = useState<ProviderModel | null>(null);
  const [deletingModel, setDeletingModel] = useState(false);

  // ─── tab state ────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'keys' | 'models'>('keys');

  // ─── load provider info via catalog (small, cached) ───────────────────────
  useEffect(() => {
    if (!providerId) return;
    let cancelled = false;
    setProviderLoading(true);
    listProviderCatalog()
      .then((items) => {
        if (cancelled) return;
        const match = items.find((p) => p.id === providerId) ?? null;
        setProvider(match);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setProviderLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [providerId]);

  // ─── load keys + models ───────────────────────────────────────────────────
  const reloadKeys = useCallback(() => {
    if (!providerId) return Promise.resolve();
    return fetchKeys({
      providerId,
      params: {
        page: keysPage,
        page_size: KEYS_PAGE_SIZE,
        search: keysSearch || undefined,
        sort_by: keysSort,
        service_type: serviceType ?? undefined,
      },
    });
  }, [providerId, keysPage, keysSearch, keysSort, serviceType, fetchKeys]);

  const reloadModels = useCallback(() => {
    if (!providerId) return Promise.resolve();
    return fetchModels({
      providerId,
      params: {
        page: modelsPage,
        page_size: MODELS_PAGE_SIZE,
        search: modelsSearch || undefined,
        sort_by: modelsSort,
        service_type: serviceType ?? undefined,
      },
    });
  }, [providerId, modelsPage, modelsSearch, modelsSort, serviceType, fetchModels]);

  useEffect(() => {
    reloadKeys().catch(handleApiError);
  }, [reloadKeys]);

  useEffect(() => {
    reloadModels().catch(handleApiError);
  }, [reloadModels]);

  // ─── handlers ─────────────────────────────────────────────────────────────
  const handleAddKey = () => {
    setCreateOpen(true);
  };

  const handleEditKey = (svc: Service) => {
    setEditing(svc);
  };

  const handleCreateKey = useCallback(
    async (payload: ServiceUpsertPayload) => {
      setIsSaving(true);
      try {
        await upsertService({ values: payload });
        showToast.success('API key created');
        setCreateOpen(false);
        await reloadKeys();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, reloadKeys],
  );

  const handleUpdateKey = useCallback(
    async (payload: Partial<ServiceUpsertPayload>, id: string) => {
      setIsSaving(true);
      try {
        await upsertService({ id, values: payload as ServiceUpsertPayload });
        showToast.success('API key updated');
        setEditing(null);
        await reloadKeys();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSaving(false);
      }
    },
    [upsertService, reloadKeys],
  );

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteService(deleteTarget.id);
      showToast.success('API key deleted');
      setDeleteTarget(null);
      await reloadKeys();
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeleting(false);
    }
  };

  const handleAddModel = () => {
    setEditingModel(null);
    setModelDrawerOpen(true);
  };

  const handleEditModel = (m: ProviderModel) => {
    setEditingModel(m);
    setModelDrawerOpen(true);
  };

  const handleSubmitModel = useCallback(
    async (payload: ModelUpsertPayload, id?: string) => {
      if (!providerId) return;
      setIsSavingModel(true);
      try {
        await upsertProviderModel({ providerId, modelId: id, values: payload });
        showToast.success(id ? 'Model updated' : 'Model created');
        setModelDrawerOpen(false);
        setEditingModel(null);
        await reloadModels();
      } catch (err) {
        handleApiError(err);
      } finally {
        setIsSavingModel(false);
      }
    },
    [providerId, upsertProviderModel, reloadModels],
  );

  const handleConfirmDeleteModel = async () => {
    if (!modelDeleteTarget || !providerId) return;
    setDeletingModel(true);
    try {
      await deleteProviderModel({ providerId, modelId: modelDeleteTarget.id });
      showToast.success('Model deleted');
      setModelDeleteTarget(null);
      await reloadModels();
    } catch (err) {
      handleApiError(err);
    } finally {
      setDeletingModel(false);
    }
  };

  // Token-bar "Name" field — a value dropdown backed by /filter-values, scoped
  // to this provider (and service_type).
  const keysFields = useMemo<TokenSearchField[]>(
    () => [
      {
        key: 'name',
        label: 'Name',
        type: 'enum',
        fetchValues: () =>
          providerId
            ? listProviderKeyFilterValues(providerId, 'name', serviceType ?? undefined)
            : Promise.resolve([]),
      },
    ],
    [providerId, serviceType],
  );
  const modelsFields = useMemo<TokenSearchField[]>(
    () => [
      {
        key: 'name',
        label: 'Name',
        type: 'enum',
        fetchValues: () =>
          providerId
            ? listProviderModelFilterValues(providerId, 'name', serviceType ?? undefined)
            : Promise.resolve([]),
      },
    ],
    [providerId, serviceType],
  );

  const keysTokens = useMemo<SearchToken[]>(
    () => (keysSearch ? [{ field: 'name', value: keysSearch }] : []),
    [keysSearch],
  );
  const handleKeysTokens = useCallback((tokens: SearchToken[]) => {
    const last = [...tokens].reverse().find((t) => t.field === 'name');
    setKeysSearch(last?.value ?? '');
    setKeysPage(1);
  }, []);
  const handleKeysSort = useCallback((s: CustomTableSortState | null) => {
    setKeysPage(1);
    if (!s) return setKeysSort('-updated_at');
    setKeysSort(s.order === 'desc' ? `-${s.field}` : s.field);
  }, []);

  const modelsTokens = useMemo<SearchToken[]>(
    () => (modelsSearch ? [{ field: 'name', value: modelsSearch }] : []),
    [modelsSearch],
  );
  const handleModelsTokens = useCallback((tokens: SearchToken[]) => {
    const last = [...tokens].reverse().find((t) => t.field === 'name');
    setModelsSearch(last?.value ?? '');
    setModelsPage(1);
  }, []);
  const handleModelsSort = useCallback((s: CustomTableSortState | null) => {
    setModelsPage(1);
    if (!s) return setModelsSort('name');
    setModelsSort(s.order === 'desc' ? `-${s.field}` : s.field);
  }, []);

  // Switching tabs starts clean — reset both tabs' search + pagination.
  const handleTabChange = useCallback((tab: 'keys' | 'models') => {
    setActiveTab(tab);
    setKeysSearch('');
    setKeysPage(1);
    setModelsSearch('');
    setModelsPage(1);
  }, []);

  // ─── columns ──────────────────────────────────────────────────────────────
  const keysColumns = useMemo<CustomTableColumn<Service>[]>(
    () => [
      {
        key: 'label',
        title: 'Name',
        dataIndex: 'label',
        sorter: true,
        render: (_v, r) => (
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium text-foreground" title={r.label ?? ''}>
              {r.label || '—'}
            </span>
            {r.description && (
              <span className="truncate text-xs text-muted-foreground">{r.description}</span>
            )}
          </div>
        ),
      },
      {
        key: 'service_type',
        title: 'Type',
        dataIndex: 'service_type',
        sorter: true,
        width: 'w-[100px]',
        render: (_v, r) => (
          <Badge
            className={cn(
              'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
              TYPE_BADGE_STYLES[r.service_type] ?? '',
            )}
          >
            {r.service_type}
          </Badge>
        ),
      },
      {
        key: 'is_default',
        title: 'Default',
        dataIndex: 'is_default',
        sorter: true,
        width: 'w-[90px]',
        render: (_v, r) =>
          r.is_default ? (
            <Badge variant="outline" className="border-primary/40 text-primary">
              Default
            </Badge>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'is_active',
        title: 'Status',
        dataIndex: 'is_active',
        sorter: true,
        width: 'w-[110px]',
        render: (_v, r) => (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
              r.is_active
                ? 'bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20 dark:text-emerald-400'
                : 'bg-muted text-muted-foreground ring-1 ring-border',
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                r.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40',
              )}
            />
            {r.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'updated_at',
        title: 'Last updated',
        dataIndex: 'updated_at',
        sorter: true,
        width: 'w-[180px]',
        render: (v) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {v ? formatDate(v as number) : '—'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[64px]',
        render: (_v, r) => (
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={(e) => {
              e.stopPropagation();
              setDeleteTarget(r);
            }}
            aria-label="Delete API key"
            className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="size-4" />
          </CustomButton>
        ),
      },
    ],
    [],
  );

  const modelsColumns = useMemo<CustomTableColumn<ProviderModel>[]>(
    () => [
      {
        key: 'name',
        title: 'Name',
        dataIndex: 'name',
        sorter: true,
        render: (_v, m) => (
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium text-foreground">
              {m.display_name || m.name}
            </span>
            {m.display_name && m.display_name !== m.name && (
              <span className="truncate text-xs text-muted-foreground">{m.name}</span>
            )}
          </div>
        ),
      },
      {
        key: 'kind',
        title: 'Kind',
        dataIndex: 'kind',
        sorter: true,
        width: 'w-[100px]',
        render: (_v, m) => (
          <Badge
            className={cn(
              'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
              TYPE_BADGE_STYLES[m.kind] ?? '',
            )}
          >
            {m.kind}
          </Badge>
        ),
      },
      {
        key: 'description',
        title: 'Description',
        dataIndex: 'description',
        render: (_v, m) => (
          <span className="line-clamp-2 text-sm text-muted-foreground">{m.description ?? '—'}</span>
        ),
      },
      {
        key: 'is_active',
        title: 'Status',
        dataIndex: 'is_active',
        sorter: true,
        width: 'w-[110px]',
        render: (_v, m) => (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
              m.is_active
                ? 'bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20 dark:text-emerald-400'
                : 'bg-muted text-muted-foreground ring-1 ring-border',
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                m.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40',
              )}
            />
            {m.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'updated_at',
        title: 'Last updated',
        dataIndex: 'updated_at',
        sorter: true,
        width: 'w-[180px]',
        render: (v) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {v ? formatDate(v as number) : '—'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: 'w-[96px]',
        render: (_v, m) => (
          <div className="flex items-center justify-end gap-1">
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                handleEditModel(m);
              }}
              aria-label="Edit model"
              className="text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Pencil className="size-4" />
            </CustomButton>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setModelDeleteTarget(m);
              }}
              aria-label="Delete model"
              className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              <Trash2 className="size-4" />
            </CustomButton>
          </div>
        ),
      },
    ],
    [],
  );

  // ─── render ───────────────────────────────────────────────────────────────
  const isKeysTab = activeTab === 'keys';

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-3">
      {/* breadcrumb */}
      <nav
        aria-label="Breadcrumb"
        className="flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground"
      >
        <Link href="/settings/model-providers" className="transition-colors hover:text-foreground">
          Model Providers
        </Link>
        <ChevronRight className="size-3.5" aria-hidden />
        <span className="truncate font-medium text-foreground">
          {providerLoading ? 'Loading…' : (provider?.display_name ?? 'Unknown provider')}
        </span>
      </nav>

      {/* tight inline header */}
      <header className="flex shrink-0 items-center gap-3">
        <ProviderLogo
          providerName={provider?.slug}
          serviceType={serviceType ?? provider?.kinds[0] ?? ''}
          className="size-10"
        />
        <div className="min-w-0 flex-1">
          <h1 className="flex items-center gap-2 font-display text-2xl font-semibold leading-tight tracking-tight text-foreground">
            <span className="truncate">
              {providerLoading ? 'Loading…' : (provider?.display_name ?? 'Unknown provider')}
            </span>
            {serviceType && (
              <Badge
                className={cn(
                  'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
                  TYPE_BADGE_STYLES[serviceType] ?? '',
                )}
              >
                {serviceType}
              </Badge>
            )}
          </h1>
          {provider?.description && (
            <p className="truncate text-xs text-muted-foreground">{provider.description}</p>
          )}
        </div>
      </header>

      {/* tab strip */}
      <div className="flex shrink-0 items-center gap-1 border-b border-border">
        <TabButton
          active={isKeysTab}
          onClick={() => handleTabChange('keys')}
          icon={<KeyRound className="size-3.5" />}
          label="API Keys"
          count={keysState.total}
        />
        <TabButton
          active={!isKeysTab}
          onClick={() => handleTabChange('models')}
          icon={<Layers className="size-3.5" />}
          label="Models"
          count={modelsState.total}
        />
      </div>

      {/* toolbar: search (left) + add (right) */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        {isKeysTab ? (
          <TokenSearchBar
            key="keys-search"
            fields={keysFields}
            value={keysTokens}
            onChange={handleKeysTokens}
            placeholder="Search keys… (e.g. name:nemotron)"
            className="w-full sm:max-w-sm"
          />
        ) : (
          <TokenSearchBar
            key="models-search"
            fields={modelsFields}
            value={modelsTokens}
            onChange={handleModelsTokens}
            placeholder="Search models… (e.g. name:gpt)"
            className="w-full sm:max-w-sm"
          />
        )}
        {isKeysTab ? (
          <CustomButton
            type="primary"
            size="sm"
            icon={<Plus className="size-4" />}
            onClick={handleAddKey}
          >
            Add API key
          </CustomButton>
        ) : (
          <CustomButton
            type="primary"
            size="sm"
            icon={<Plus className="size-4" />}
            onClick={handleAddModel}
          >
            Add model
          </CustomButton>
        )}
      </div>

      {/* table panes — animated swap; this is the only scroll surface */}
      <div className="mt-2 flex min-h-0 flex-1 flex-col">
        <AnimatePresence mode="wait">
          {isKeysTab ? (
            <motion.div
              key="keys"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="flex min-h-0 flex-1 flex-col"
            >
              <CustomTable
                columns={keysColumns}
                dataSource={keysState.items}
                rowKey="id"
                loading={keysState.loading}
                onRowClick={(r) => handleEditKey(r)}
                onSortChange={handleKeysSort}
                initialSort={{ field: 'updated_at', order: 'desc' }}
                pagination={{
                  current: keysPage,
                  pageSize: KEYS_PAGE_SIZE,
                  total: keysState.total,
                  onChange: (p) => setKeysPage(p),
                }}
                emptyState={
                  <div className="flex flex-col items-center gap-3 py-12 text-center">
                    <KeyRound className="size-8 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">
                      No API keys for this provider
                    </p>
                    <p className="max-w-xs text-xs text-muted-foreground">
                      Add a key to start using this provider in your agents.
                    </p>
                    <CustomButton
                      type="primary"
                      size="sm"
                      icon={<Plus className="size-4" />}
                      onClick={handleAddKey}
                    >
                      Add API key
                    </CustomButton>
                  </div>
                }
              />
            </motion.div>
          ) : (
            <motion.div
              key="models"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="flex min-h-0 flex-1 flex-col"
            >
              <CustomTable
                columns={modelsColumns}
                dataSource={modelsState.items}
                rowKey="id"
                loading={modelsState.loading}
                onRowClick={(r) => handleEditModel(r)}
                onSortChange={handleModelsSort}
                initialSort={{ field: 'name', order: 'asc' }}
                pagination={{
                  current: modelsPage,
                  pageSize: MODELS_PAGE_SIZE,
                  total: modelsState.total,
                  onChange: (p) => setModelsPage(p),
                }}
                emptyState={
                  <div className="flex flex-col items-center gap-3 py-12 text-center">
                    <Layers className="size-8 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">No models registered</p>
                    <p className="max-w-xs text-xs text-muted-foreground">
                      Add a model to make it available in the catalog for this provider.
                    </p>
                    <CustomButton
                      type="primary"
                      size="sm"
                      icon={<Plus className="size-4" />}
                      onClick={handleAddModel}
                    >
                      Add model
                    </CustomButton>
                  </div>
                }
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* create drawer */}
      <ApiKeyCreateDrawer
        open={createOpen}
        lockedProviderId={providerId}
        defaultServiceType={serviceType ?? (provider?.kinds[0] as ServiceKind) ?? null}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreateKey}
        isPending={isSaving}
      />

      {/* edit drawer */}
      <ApiKeyEditDrawer
        open={!!editing}
        editing={editing}
        onClose={() => setEditing(null)}
        onSubmit={handleUpdateKey}
        isPending={isSaving}
      />

      {/* delete confirm */}
      <CustomModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete API key"
        description={
          deleteTarget
            ? `Delete "${deleteTarget.label || 'this API key'}"? This action cannot be undone.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleConfirmDelete}
      />

      {/* model drawer */}
      <ModelFormDrawer
        open={modelDrawerOpen}
        editing={editingModel}
        defaultKind={serviceType ?? (provider?.kinds[0] as ServiceKind) ?? null}
        allowedKinds={
          serviceType ? [serviceType] : ((provider?.kinds as ServiceKind[]) ?? undefined)
        }
        onClose={() => {
          setModelDrawerOpen(false);
          setEditingModel(null);
        }}
        onSubmit={handleSubmitModel}
        isPending={isSavingModel}
      />

      {/* model delete confirm */}
      <CustomModal
        open={!!modelDeleteTarget}
        onClose={() => !deletingModel && setModelDeleteTarget(null)}
        title="Delete model"
        description={
          modelDeleteTarget
            ? `Delete "${modelDeleteTarget.display_name || modelDeleteTarget.name}"? Agents referencing this model will fail until they're reconfigured.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deletingModel}
        onConfirm={handleConfirmDeleteModel}
      />
    </div>
  );
}

// ─── tab button (inline, underline indicator) ──────────────────────────────
interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon?: React.ReactNode;
  label: string;
  count?: number;
  muted?: boolean;
}

function TabButton({ active, onClick, icon, label, count, muted }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'relative -mb-px inline-flex cursor-pointer items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
        active
          ? muted
            ? 'border-foreground/60 text-foreground'
            : 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )}
    >
      {icon}
      <span>{label}</span>
      {typeof count === 'number' && count > 0 && (
        <Badge
          variant="secondary"
          className={cn(
            'h-5 px-1.5 text-[10px] tabular-nums',
            active && !muted && 'bg-primary/10 text-primary hover:bg-primary/10',
          )}
        >
          {count}
        </Badge>
      )}
    </button>
  );
}

'use client';

import {
  deleteProviderAtom,
  fetchModelsAtom,
  modelsAtom,
  upsertProviderAtom,
} from '@/atoms/ProviderAtom';
import ApiKeyUpsertModal from '@/components/service-providers/ApiKeyUpsertModal';
import ModelsPanel from '@/components/service-providers/ModelsPanel';
import ProviderUpsertModal from '@/components/service-providers/ProviderUpsertModal';
import { ActionMenu, CustomButton } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import {
  deleteApiKey,
  getApiKeyPlaintext,
  getServiceProvider,
  listApiKeysByProvider,
  type ApiKeyListRow,
} from '@/services/providerService';
import type { ServiceProvider, ServiceProviderUpsertPayload } from '@/types/provider';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Copy,
  Edit,
  Eye,
  EyeOff,
  Key,
  Loader2,
  Plus,
  Server,
  Trash2,
} from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { STATUS_STYLES, TYPE_BADGE_STYLES, TYPE_ICON_STYLES, TYPE_ICONS } from './constants';

export default function ServiceProviderDetailPage() {
  const router = useRouter();
  const params = useParams<{ providerId: string }>();
  const providerId = Number(params.providerId);

  const [, fetchModels] = useAtom(fetchModelsAtom);
  const [, upsertProvider] = useAtom(upsertProviderAtom);
  const [, removeProvider] = useAtom(deleteProviderAtom);

  const [provider, setProvider] = useState<ServiceProvider | null>(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [keys, setKeys] = useState<ApiKeyListRow[]>([]);
  const [keysLoading, setKeysLoading] = useState(false);
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<ApiKeyListRow | null>(null);
  const [revealedKeyId, setRevealedKeyId] = useState<number | null>(null);
  const [revealedKeyValue, setRevealedKeyValue] = useState<string | null>(null);
  const [revealingKeyId, setRevealingKeyId] = useState<number | null>(null);

  const loadKeys = useCallback(async () => {
    if (!Number.isFinite(providerId)) return;
    setKeysLoading(true);
    try {
      const result = await listApiKeysByProvider({
        service_provider_id: providerId,
        page: 1,
        page_size: 100,
      });
      setKeys(result.keys);
    } catch (error) {
      handleApiError(error);
    } finally {
      setKeysLoading(false);
    }
  }, [providerId]);

  const loadProvider = useCallback(async () => {
    if (!Number.isFinite(providerId)) return;
    setLoading(true);
    setRevealedKeyId(null);
    setRevealedKeyValue(null);
    try {
      const data = await getServiceProvider(providerId);
      setProvider(data);
      fetchModels({ service_provider_id: providerId, page: 1, page_size: 10 }).catch(
        handleApiError,
      );
      loadKeys();
    } catch (error) {
      handleApiError(error);
      setProvider(null);
    } finally {
      setLoading(false);
    }
  }, [providerId, fetchModels, loadKeys]);

  const handleReveal = useCallback(
    async (keyId: number) => {
      if (revealedKeyId === keyId) {
        setRevealedKeyId(null);
        setRevealedKeyValue(null);
        return;
      }
      setRevealingKeyId(keyId);
      try {
        const detail = await getApiKeyPlaintext(keyId);
        setRevealedKeyId(keyId);
        setRevealedKeyValue(detail.api_key);
      } catch (error) {
        handleApiError(error);
      } finally {
        setRevealingKeyId(null);
      }
    },
    [revealedKeyId],
  );

  const handleCopy = useCallback(async (keyId: number) => {
    try {
      const detail = await getApiKeyPlaintext(keyId);
      await navigator.clipboard.writeText(detail.api_key);
      showToast.success('API key copied to clipboard');
    } catch (error) {
      handleApiError(error);
    }
  }, []);

  const handleAddKey = useCallback(() => {
    setEditingKey(null);
    setKeyModalOpen(true);
  }, []);

  const handleEditKey = useCallback((row: ApiKeyListRow) => {
    setEditingKey(row);
    setKeyModalOpen(true);
  }, []);

  const handleDeleteKey = useCallback(
    async (row: ApiKeyListRow) => {
      try {
        await deleteApiKey(row.id);
        showToast.success('API key deleted');
        await loadKeys();
        await loadProvider();
      } catch (error) {
        handleApiError(error);
      }
    },
    [loadKeys, loadProvider],
  );

  const handleKeySaved = useCallback(async () => {
    await loadKeys();
    await loadProvider();
  }, [loadKeys, loadProvider]);

  useEffect(() => {
    loadProvider();
  }, [loadProvider]);

  const handleSubmit = useCallback(
    async (payload: ServiceProviderUpsertPayload) => {
      try {
        await upsertProvider(payload);
        showToast.success('Provider updated');
        await loadProvider();
      } catch (error) {
        handleApiError(error);
        throw error;
      }
    },
    [upsertProvider, loadProvider],
  );

  const handleDelete = useCallback(async () => {
    if (!provider) return;
    if (provider.is_system) {
      showToast.error('System providers cannot be deleted');
      return;
    }
    if (
      !window.confirm(
        `Delete "${provider.display_name}"? This also removes its API key and unlinks any models using it.`,
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await removeProvider(provider.id);
      showToast.success('Provider deleted');
      router.push('/service-providers');
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeleting(false);
    }
  }, [provider, removeProvider, router]);

  const goBack = useCallback(() => router.push('/service-providers'), [router]);

  // ── Loading / Not found ────────────────────────────────────────

  if (loading) {
    return (
      <div className="animate-page flex h-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!provider) {
    return (
      <div className="animate-page flex h-full flex-col items-center justify-center gap-3 p-6">
        <Server className="size-10 text-muted-foreground" />
        <p className="text-sm font-medium text-foreground">Service provider not found</p>
        <CustomButton type="default" icon={<ArrowLeft />} onClick={goBack}>
          Back to providers
        </CustomButton>
      </div>
    );
  }

  const typeKey = provider.provider_type ?? '';
  const statusKey = (provider.status ?? 'active').toLowerCase();

  return (
    <div className="animate-page flex h-full flex-col gap-4 p-5">
      {/* Compact header strip */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <button
            onClick={goBack}
            className="flex size-8 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft className="size-4" />
          </button>
          <div
            className={cn(
              'flex size-9 shrink-0 items-center justify-center rounded-lg',
              TYPE_ICON_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {TYPE_ICONS[typeKey] ?? <Server className="size-4" />}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <h1 className="truncate text-lg font-semibold tracking-tight text-foreground">
                {provider.display_name}
              </h1>
              <Badge
                className={cn(
                  'text-[10px] font-semibold uppercase tracking-wider',
                  TYPE_BADGE_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
                )}
              >
                {typeKey}
              </Badge>
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <span
                  className={cn(
                    'size-1.5 rounded-full',
                    STATUS_STYLES[statusKey] ?? STATUS_STYLES.inactive,
                  )}
                />
                <span className="capitalize">{statusKey}</span>
              </span>
              {provider.is_system && (
                <Badge className="bg-muted text-[10px] font-medium text-muted-foreground">
                  System
                </Badge>
              )}
            </div>
            <p className="truncate text-[11px] text-muted-foreground">
              <span className="font-mono">{provider.name}</span>
              {provider.description && (
                <>
                  <span className="mx-1.5 text-border">·</span>
                  <span>{provider.description}</span>
                </>
              )}
              {provider.base_url && (
                <>
                  <span className="mx-1.5 text-border">·</span>
                  <span className="font-mono">{provider.base_url}</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <CustomButton type="default" size="sm" icon={<Edit />} onClick={() => setEditOpen(true)}>
            Edit
          </CustomButton>
          {!provider.is_system && (
            <CustomButton
              type="default"
              size="sm"
              icon={<Trash2 />}
              onClick={handleDelete}
              loading={deleting}
            >
              Delete
            </CustomButton>
          )}
        </div>
      </div>

      {/* API Keys section — multi-key list */}
      <div className="flex flex-col rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Key className="size-3.5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">API Keys</h2>
              <p className="text-[11px] text-muted-foreground">
                {keys.length} {keys.length === 1 ? 'key' : 'keys'} for this provider
              </p>
            </div>
          </div>
          <CustomButton type="primary" size="sm" icon={<Plus />} onClick={handleAddKey}>
            Add Key
          </CustomButton>
        </div>

        {keysLoading && keys.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading keys...
          </div>
        ) : keys.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Key className="size-5 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">No API keys yet for this provider.</p>
            <CustomButton type="default" size="sm" icon={<Plus />} onClick={handleAddKey}>
              Add API Key
            </CustomButton>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {keys.map((row) => {
              const isRevealed = revealedKeyId === row.id;
              const isLoading = revealingKeyId === row.id;
              const displayValue =
                isRevealed && revealedKeyValue ? revealedKeyValue : row.api_key_hint;
              return (
                <div
                  key={row.id}
                  className="flex flex-wrap items-center gap-3 px-4 py-2.5 transition-colors hover:bg-accent/30"
                >
                  <div className="min-w-30 flex-1 truncate text-sm font-medium text-foreground">
                    {row.name}
                    {row.description && (
                      <span className="ml-1.5 text-[11px] font-normal text-muted-foreground">
                        — {row.description}
                      </span>
                    )}
                  </div>
                  <div className="flex min-w-50 flex-2 items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-1">
                    <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
                      {isLoading ? 'Loading...' : displayValue}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleReveal(row.id)}
                      disabled={isLoading}
                      className="flex size-6 cursor-pointer items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                      title={isRevealed ? 'Hide' : 'Reveal'}
                    >
                      {isLoading ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : isRevealed ? (
                        <EyeOff className="size-3.5" />
                      ) : (
                        <Eye className="size-3.5" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCopy(row.id)}
                      className="flex size-6 cursor-pointer items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                      title="Copy"
                    >
                      <Copy className="size-3.5" />
                    </button>
                  </div>
                  <span className="flex items-center gap-1 text-[11px] capitalize text-muted-foreground">
                    <span
                      className={cn(
                        'size-1.5 rounded-full',
                        row.status === 'active' ? 'bg-emerald-500' : 'bg-amber-500',
                      )}
                    />
                    {row.status}
                  </span>
                  <span
                    className={cn(
                      'flex items-center gap-1 whitespace-nowrap text-[11px]',
                      row.is_valid
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-amber-600 dark:text-amber-400',
                    )}
                  >
                    {row.is_valid ? (
                      <CheckCircle2 className="size-3.5" />
                    ) : (
                      <AlertCircle className="size-3.5" />
                    )}
                    {row.is_valid ? 'Valid' : 'Not validated'}
                  </span>
                  {row.updated_at != null && (
                    <span className="whitespace-nowrap text-[11px] text-muted-foreground">
                      {formatDate(row.updated_at, 'DD MMM YYYY')}
                    </span>
                  )}
                  <ActionMenu
                    onEdit={() => handleEditKey(row)}
                    onDelete={() => handleDeleteKey(row)}
                    itemName={row.name}
                    deleteDescription={`Delete API key "${row.name}"? Models pointing at this key will be unlinked.`}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Models — full width */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <ModelsPanel selectedProvider={provider} onBack={goBack} />
      </div>

      {/* Provider edit modal */}
      <ProviderUpsertModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSubmit={handleSubmit}
        provider={provider}
      />

      {/* Multi-key add/edit modal */}
      <ApiKeyUpsertModal
        open={keyModalOpen}
        onClose={() => setKeyModalOpen(false)}
        onSaved={handleKeySaved}
        serviceProviderId={providerId}
        apiKey={editingKey}
      />
    </div>
  );
}

// ── small helper ───────────────────────────────────────────────────

interface RowProps {
  label: string;
  value?: string;
  valueNode?: React.ReactNode;
}

function Row({ label, value, valueNode }: RowProps) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground">{valueNode ?? value}</span>
    </div>
  );
}

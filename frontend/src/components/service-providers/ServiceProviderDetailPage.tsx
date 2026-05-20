'use client';

import { deleteProviderAtom, fetchModelsAtom, modelsAtom } from '@/atoms/ProviderAtom';

import ApiKeyUpsertModal from '@/components/service-providers/ApiKeyUpsertModal';
import ModelsPanel from '@/components/service-providers/ModelsPanel';

import ProviderLogo from '@/components/service-providers/ProviderLogo';
import { ActionMenu, CustomButton, CustomTab } from '@/components/shared';
import ToneLoader from '@/components/shared/ToneLoader';
import { Badge } from '@/components/ui/badge';
import {
  deleteApiKey,
  getApiKeyPlaintext,
  getServiceProvider,
  listApiKeysByAccount,
  type ApiKeyListRow,
} from '@/services/providerService';
import type { ServiceProvider } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import {
  AlertCircle,
  ArrowLeft,
  Box,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  Globe,
  Key,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { STATUS_STYLES, TYPE_BADGE_STYLES } from './constants';

export default function ServiceProviderDetailPage() {
  const router = useRouter();
  const params = useParams<{ providerId: string }>();
  const searchParams = useSearchParams();
  const providerId = Number(params.providerId);
  const accountId = searchParams.get('accountId') ? Number(searchParams.get('accountId')) : null;
  const accountNameParam = searchParams.get('accountName');

  const [modelsState] = useAtom(modelsAtom);
  const [, fetchModels] = useAtom(fetchModelsAtom);
  const [, removeProvider] = useAtom(deleteProviderAtom);

  const [provider, setProvider] = useState<ServiceProvider | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  // API Keys
  const [keys, setKeys] = useState<ApiKeyListRow[]>([]);
  const [keysLoading, setKeysLoading] = useState(false);
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<ApiKeyListRow | null>(null);
  const [revealedKeyId, setRevealedKeyId] = useState<number | null>(null);
  const [revealedKeyValue, setRevealedKeyValue] = useState<string | null>(null);
  const [revealingKeyId, setRevealingKeyId] = useState<number | null>(null);

  // ── Data loading ─────────────────────────────────────────────────

  const loadKeys = useCallback(async () => {
    if (!accountId) {
      setKeys([]);
      return;
    }
    setKeysLoading(true);
    try {
      const result = await listApiKeysByAccount({ account_id: accountId, page: 1, page_size: 100 });
      setKeys(result.keys);
    } catch (error) {
      handleApiError(error);
    } finally {
      setKeysLoading(false);
    }
  }, [accountId]);

  const loadProvider = useCallback(async () => {
    if (!Number.isFinite(providerId)) return;
    setLoading(true);
    setRevealedKeyId(null);
    setRevealedKeyValue(null);
    try {
      const data = await getServiceProvider(providerId);
      setProvider(data);
      fetchModels({ model_provider_menu_id: providerId, page: 1, page_size: 10 }).catch(
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

  useEffect(() => {
    loadProvider();
  }, [loadProvider]);

  // ── API Key handlers ─────────────────────────────────────────────

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
      showToast.success('Copied to clipboard');
    } catch (error) {
      handleApiError(error);
    }
  }, []);

  const handleDeleteKey = useCallback(
    async (row: ApiKeyListRow) => {
      try {
        await deleteApiKey(row.id);
        showToast.success('API key deleted');
        await loadKeys();
      } catch (error) {
        handleApiError(error);
      }
    },
    [loadKeys],
  );

  const handleKeySaved = useCallback(async () => {
    await loadKeys();
  }, [loadKeys]);

  // ── Provider handlers ────────────────────────────────────────────

  const handleDelete = useCallback(async () => {
    if (!provider) return;
    if (provider.is_system) {
      showToast.error('System providers cannot be deleted');
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

  // ── Tab content ──────────────────────────────────────────────────

  const tabItems = useMemo(() => {
    if (!provider) return [];

    return [
      {
        key: 'keys',
        label: (
          <span className="flex items-center gap-1.5">
            <Key className="size-3.5" />
            API Keys
            <span className="ml-0.5 rounded-full bg-muted px-1.5 py-px text-[10px] tabular-nums text-muted-foreground">
              {keys.length}
            </span>
          </span>
        ),
        children: (
          <div className="h-full overflow-auto px-6 py-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Credentials used by services and models for this provider
              </p>
              <CustomButton
                type="primary"
                size="sm"
                icon={<Plus />}
                onClick={() => {
                  setEditingKey(null);
                  setKeyModalOpen(true);
                }}
              >
                Add Key
              </CustomButton>
            </div>
            {keysLoading && keys.length === 0 ? (
              <div className="flex items-center justify-center gap-2 py-8 text-xs text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading...
              </div>
            ) : keys.length === 0 ? (
              <div className="flex flex-col items-center gap-3 py-10">
                <div className="flex size-11 items-center justify-center rounded-xl bg-muted">
                  <Key className="size-5 text-muted-foreground" />
                </div>
                <p className="text-xs text-muted-foreground">No API keys yet</p>
                <CustomButton
                  type="default"
                  size="sm"
                  icon={<Plus />}
                  onClick={() => {
                    setEditingKey(null);
                    setKeyModalOpen(true);
                  }}
                >
                  Add Key
                </CustomButton>
              </div>
            ) : (
              <div className="space-y-2">
                {keys.map((row) => {
                  const isRevealed = revealedKeyId === row.id;
                  const isRevLoading = revealingKeyId === row.id;
                  const displayValue =
                    isRevealed && revealedKeyValue ? revealedKeyValue : row.api_key_hint;
                  return (
                    <div
                      key={row.id}
                      className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-background px-4 py-3 transition-colors hover:bg-accent/20"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-foreground">{row.name}</div>
                        {row.description && (
                          <p className="text-[11px] text-muted-foreground">{row.description}</p>
                        )}
                      </div>

                      {/* Key value display */}
                      <div className="flex items-center gap-1 rounded-md bg-muted/50 px-2.5 py-1.5">
                        <span className="max-w-[200px] truncate font-mono text-xs text-foreground">
                          {isRevLoading ? '...' : displayValue}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleReveal(row.id)}
                          disabled={isRevLoading}
                          className="flex size-6 cursor-pointer items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-50"
                        >
                          {isRevLoading ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : isRevealed ? (
                            <EyeOff className="size-3" />
                          ) : (
                            <Eye className="size-3" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCopy(row.id)}
                          className="flex size-6 cursor-pointer items-center justify-center rounded text-muted-foreground hover:text-foreground"
                        >
                          <Copy className="size-3" />
                        </button>
                      </div>

                      {/* Status + Validation */}
                      <div className="flex items-center gap-3">
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
                            'flex items-center gap-1 text-[11px]',
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
                          {row.is_valid ? 'Valid' : 'Unverified'}
                        </span>
                      </div>

                      <ActionMenu
                        onEdit={() => {
                          setEditingKey(row);
                          setKeyModalOpen(true);
                        }}
                        onDelete={() => handleDeleteKey(row)}
                        itemName={row.name}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ),
      },
      {
        key: 'models',
        label: (
          <span className="flex items-center gap-1.5">
            <Box className="size-3.5" />
            Models
            <span className="ml-0.5 rounded-full bg-muted px-1.5 py-px text-[10px] tabular-nums text-muted-foreground">
              {modelsState.pagination?.total ?? provider.models?.length ?? 0}
            </span>
          </span>
        ),
        children: (
          <div className="flex h-full min-h-0 flex-col overflow-hidden">
            <ModelsPanel selectedProvider={provider} onBack={goBack} compact />
          </div>
        ),
      },
    ];
  }, [
    provider,
    keys,
    keysLoading,
    revealedKeyId,
    revealedKeyValue,
    revealingKeyId,
    modelsState.pagination,
    handleReveal,
    handleCopy,
    handleDeleteKey,
    goBack,
  ]);

  // ── Loading / Not found ────────────────────────────────────────

  if (loading) {
    return (
      <div className="animate-page flex h-full items-center justify-center">
        <ToneLoader label="Loading provider..." />
      </div>
    );
  }

  if (!provider) {
    return (
      <div className="animate-page flex h-full flex-col items-center justify-center gap-4 p-6">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-muted">
          <AlertCircle className="size-6 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground">Service provider not found</p>
        <CustomButton type="default" icon={<ArrowLeft />} onClick={goBack}>
          Back to services
        </CustomButton>
      </div>
    );
  }

  const typeKey = provider.provider_type ?? '';
  const statusKey = (provider.status ?? 'active').toLowerCase();

  return (
    <div className="animate-page flex h-full flex-col overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-border bg-card px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-center gap-4">
            <button
              onClick={goBack}
              className="flex size-9 cursor-pointer items-center justify-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="Back"
            >
              <ArrowLeft className="size-4" />
            </button>

            <ProviderLogo
              providerName={provider.name}
              serviceType={typeKey}
              className="size-12 rounded-xl"
              imgSize={28}
            />

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  {accountNameParam ?? provider.display_name}
                </h1>
                <Badge
                  className={cn(
                    'text-[10px] font-semibold uppercase tracking-wider',
                    TYPE_BADGE_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
                  )}
                >
                  {typeKey}
                </Badge>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span
                    className={cn(
                      'size-2 rounded-full',
                      STATUS_STYLES[statusKey] ?? STATUS_STYLES.inactive,
                    )}
                  />
                  <span className="capitalize">{statusKey}</span>
                </span>
                {provider.is_system && (
                  <Badge className="bg-muted text-[10px] font-medium text-muted-foreground hover:bg-muted">
                    System
                  </Badge>
                )}
              </div>

              <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="font-mono">{provider.name}</span>
                {provider.description && <span>{provider.description}</span>}
                {provider.base_url && (
                  <span className="flex items-center gap-1">
                    <Globe className="size-3" />
                    <span className="font-mono">{provider.base_url}</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {!provider.is_system && (
            <CustomButton
              type="danger"
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

      {/* ── Tabbed content ──────────────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CustomTab
          items={tabItems}
          defaultActiveKey="keys"
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
          tabBarClassName="shrink-0 border-b border-border bg-background px-6"
          contentClassName="min-h-0 flex-1 overflow-hidden"
        />
      </div>

      {/* ── Modals ──────────────────────────────────────────────────── */}

      <ApiKeyUpsertModal
        open={keyModalOpen}
        onClose={() => setKeyModalOpen(false)}
        onSaved={handleKeySaved}
        accountId={accountId!}
        apiKey={editingKey}
      />
    </div>
  );
}

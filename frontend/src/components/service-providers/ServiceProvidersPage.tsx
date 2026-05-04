'use client';

import {
  deleteProviderAtom,
  fetchProvidersAtom,
  providersAtom,
  upsertProviderAtom,
} from '@/atoms/ProviderAtom';
import ProviderCard from '@/components/service-providers/ProviderCard';
import ProviderUpsertModal from '@/components/service-providers/ProviderUpsertModal';
import { CustomButton } from '@/components/shared';
import type { ServiceProvider, ServiceProviderUpsertPayload } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Loader2, Plus, Search, Server } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { PROVIDER_TYPE_TABS, PROVIDERS_PAGE_SIZE } from './constants';

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [providersState] = useAtom(providersAtom);
  const [, fetchProviders] = useAtom(fetchProvidersAtom);
  const [, upsertProvider] = useAtom(upsertProviderAtom);
  const [, removeProvider] = useAtom(deleteProviderAtom);

  const hasFetchedRef = useRef(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [providerModalOpen, setProviderModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ServiceProvider | null>(null);

  // ── Helpers ──────────────────────────────────────────────────────

  const buildParams = useCallback(
    (page: number, nameOverride?: string) => {
      const params: Record<string, unknown> = { page, page_size: PROVIDERS_PAGE_SIZE };
      if (activeTab !== 'all') params.provider_type = activeTab;
      const name = nameOverride ?? searchQuery;
      if (name.trim()) params.name = name.trim();
      return params;
    },
    [activeTab, searchQuery],
  );

  // ── Initial Fetch ────────────────────────────────────────────────

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    fetchProviders({ params: buildParams(1) }).catch(handleApiError);
  }, [fetchProviders, buildParams]);

  // ── Debounced provider search ────────────────────────────────────

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedSearch = useMemo(
    () => (query: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        fetchProviders({ params: buildParams(1, query) }).catch(handleApiError);
      }, 300);
    },
    [fetchProviders, buildParams],
  );

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    },
    [],
  );

  // ── Tab change ───────────────────────────────────────────────────

  const handleTabChange = useCallback(
    (tab: string) => {
      setActiveTab(tab);
      const params: Record<string, unknown> = { page: 1, page_size: PROVIDERS_PAGE_SIZE };
      if (tab !== 'all') params.provider_type = tab;
      fetchProviders({ params }).catch(handleApiError);
    },
    [fetchProviders],
  );

  // ── Infinite Scroll ──────────────────────────────────────────────

  const hasMore =
    providersState.pagination != null &&
    providersState.pagination.page < providersState.pagination.total_pages;

  const loadMore = useCallback(() => {
    if (providersState.loadingMore || providersState.loading || !hasMore) return;
    const nextPage = (providersState.pagination?.page ?? 0) + 1;
    fetchProviders({ params: buildParams(nextPage), append: true }).catch(handleApiError);
  }, [
    fetchProviders,
    providersState.loadingMore,
    providersState.loading,
    hasMore,
    providersState.pagination,
    buildParams,
  ]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const container = scrollContainerRef.current;
    if (!sentinel || !container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { root: container, rootMargin: '100px' },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  // ── Provider CRUD ────────────────────────────────────────────────

  const handleProviderSelect = useCallback(
    (provider: ServiceProvider) => router.push(`/service-providers/${provider.id}`),
    [router],
  );

  const refreshProviders = useCallback(
    () => fetchProviders({ params: buildParams(1) }),
    [fetchProviders, buildParams],
  );

  const handleProviderSubmit = useCallback(
    async (payload: ServiceProviderUpsertPayload) => {
      try {
        await upsertProvider(payload);
        showToast.success(payload.id ? 'Provider updated' : 'Provider created');
        await refreshProviders();
      } catch (error) {
        handleApiError(error);
        throw error;
      }
    },
    [upsertProvider, refreshProviders],
  );

  const handleProviderDelete = useCallback(
    async (provider: ServiceProvider) => {
      try {
        await removeProvider(provider.id);
        showToast.success('Provider deleted');
        await refreshProviders();
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeProvider, refreshProviders],
  );

  const openEditProvider = useCallback((provider: ServiceProvider) => {
    setEditingProvider(provider);
    setProviderModalOpen(true);
  }, []);

  const openCreateProvider = useCallback(() => {
    setEditingProvider(null);
    setProviderModalOpen(true);
  }, []);

  // ── Render ───────────────────────────────────────────────────────

  return (
    <div className="animate-page flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Service Providers
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage LLM, STT, and TTS providers and their models
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={openCreateProvider}>
          Add Provider
        </CustomButton>
      </div>

      {/* Single-pane provider list (clicking a card navigates to /service-providers/{id}) */}
      <div className="flex min-h-0 flex-1 gap-5">
        <div className={cn('flex min-h-0 w-full flex-col')}>
          {/* Search */}
          <div className="relative mb-3">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search providers..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                debouncedSearch(e.target.value);
              }}
              className="h-9 w-full cursor-text rounded-lg border border-input bg-background pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
            />
          </div>

          {/* Type Tabs */}
          <div className="mb-3 flex gap-1 rounded-lg border border-border bg-muted/40 p-1">
            {PROVIDER_TYPE_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={cn(
                  'flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                  activeTab === tab.key
                    ? 'bg-background text-foreground shadow-sm ring-1 ring-border/50'
                    : 'text-muted-foreground hover:bg-background/50 hover:text-foreground',
                )}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Provider Cards with infinite scroll */}
          <div
            ref={scrollContainerRef}
            className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto"
          >
            {providersState.loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
                >
                  <div className="size-9 shrink-0 animate-pulse rounded-lg bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-28 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                  </div>
                </div>
              ))
            ) : providersState.providers.length === 0 ? (
              <div className="flex flex-col items-center gap-3 py-16">
                <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
                  <Server className="size-5 text-muted-foreground" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-foreground">
                    {searchQuery ? 'No matches found' : 'No providers yet'}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {searchQuery ? 'Try a different search term' : 'Add a provider to get started'}
                  </p>
                </div>
                {!searchQuery && (
                  <CustomButton
                    type="primary"
                    icon={<Plus />}
                    size="sm"
                    onClick={openCreateProvider}
                  >
                    Add Provider
                  </CustomButton>
                )}
              </div>
            ) : (
              <>
                {providersState.providers.map((provider) => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    selected={false}
                    onSelect={() => handleProviderSelect(provider)}
                    onEdit={() => openEditProvider(provider)}
                    onDelete={() => handleProviderDelete(provider)}
                  />
                ))}

                {/* Infinite scroll sentinel */}
                <div ref={sentinelRef} className="shrink-0">
                  {providersState.loadingMore && (
                    <div className="flex items-center justify-center gap-2 py-3">
                      <Loader2 className="size-4 animate-spin text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">Loading more...</span>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Provider count footer */}
          {!providersState.loading && providersState.providers.length > 0 && (
            <div className="mt-2 border-t border-border pt-2 text-center text-xs text-muted-foreground">
              {providersState.providers.length} provider
              {providersState.providers.length !== 1 ? 's' : ''} loaded
              {providersState.pagination &&
                providersState.pagination.total > providersState.providers.length && (
                  <span> of {providersState.pagination.total} total</span>
                )}
            </div>
          )}
        </div>
      </div>

      {/* Provider Modal */}
      <ProviderUpsertModal
        open={providerModalOpen}
        onClose={() => setProviderModalOpen(false)}
        onSubmit={handleProviderSubmit}
        provider={editingProvider}
      />
    </div>
  );
}

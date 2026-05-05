'use client';

import { fetchServicesAtom, servicesAtom, upsertServiceAtom } from '@/atoms/ProviderAtom';
import ServiceCard from '@/components/service-providers/ServiceCard';
import ServiceUpsertModal from '@/components/service-providers/ServiceUpsertModal';
import { CustomButton } from '@/components/shared';
import { deleteService as deleteServiceApi } from '@/services/providerService';
import type { Service, ServiceUpsertPayload } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Loader2, Plug, Plus, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { PROVIDER_TYPE_TABS, SERVICES_PAGE_SIZE } from './constants';

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [servicesState] = useAtom(servicesAtom);
  const [, fetchServices] = useAtom(fetchServicesAtom);
  const [, upsertSvc] = useAtom(upsertServiceAtom);

  const hasFetchedRef = useRef(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);

  // ── Helpers ──────────────────────────────────────────────────────

  const buildParams = useCallback(
    (page: number, nameOverride?: string) => {
      const params: Record<string, unknown> = { page, page_size: SERVICES_PAGE_SIZE };
      if (activeTab !== 'all') params.service_type = activeTab;
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
    fetchServices({ params: buildParams(1) }).catch(handleApiError);
  }, [fetchServices, buildParams]);

  // ── Debounced search ─────────────────────────────────────────────

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const debouncedSearch = useMemo(
    () => (query: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        fetchServices({ params: buildParams(1, query) }).catch(handleApiError);
      }, 300);
    },
    [fetchServices, buildParams],
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
      const params: Record<string, unknown> = { page: 1, page_size: SERVICES_PAGE_SIZE };
      if (tab !== 'all') params.service_type = tab;
      fetchServices({ params }).catch(handleApiError);
    },
    [fetchServices],
  );

  // ── Infinite Scroll ──────────────────────────────────────────────

  const hasMore =
    servicesState.pagination != null &&
    servicesState.pagination.page < servicesState.pagination.total_pages;

  const loadMore = useCallback(() => {
    if (servicesState.loadingMore || servicesState.loading || !hasMore) return;
    const nextPage = (servicesState.pagination?.page ?? 0) + 1;
    fetchServices({ params: buildParams(nextPage), append: true }).catch(handleApiError);
  }, [
    fetchServices,
    servicesState.loadingMore,
    servicesState.loading,
    hasMore,
    servicesState.pagination,
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
      { root: container, rootMargin: '200px' },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  // ── CRUD ─────────────────────────────────────────────────────────

  const refreshServices = useCallback(
    () => fetchServices({ params: buildParams(1) }),
    [fetchServices, buildParams],
  );

  const handleSubmit = useCallback(
    async (payload: ServiceUpsertPayload) => {
      try {
        await upsertSvc(payload);
        showToast.success(payload.uuid ? 'Service updated' : 'Service created');
        await refreshServices();
      } catch (error) {
        handleApiError(error);
        throw error;
      }
    },
    [upsertSvc, refreshServices],
  );

  const handleDelete = useCallback(
    async (svc: Service) => {
      try {
        await deleteServiceApi(svc.uuid);
        showToast.success('Service deleted');
        await refreshServices();
      } catch (error) {
        handleApiError(error);
      }
    },
    [refreshServices],
  );

  const openEdit = useCallback((svc: Service) => {
    setEditingService(svc);
    setModalOpen(true);
  }, []);

  const openCreate = useCallback(() => {
    setEditingService(null);
    setModalOpen(true);
  }, []);

  // ── Render ───────────────────────────────────────────────────────

  const total = servicesState.pagination?.total ?? servicesState.services.length;

  return (
    <div className="animate-page flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Services</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your LLM, STT, and TTS service configurations
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={openCreate}>
          Add Service
        </CustomButton>
      </div>

      {/* Toolbar: Search + Tabs */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              debouncedSearch(e.target.value);
            }}
            className="h-9 w-full cursor-text rounded-lg border border-input bg-background pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
          />
        </div>
        <div className="flex gap-1 rounded-lg border border-border bg-muted/40 p-1">
          {PROVIDER_TYPE_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={cn(
                'flex cursor-pointer items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all',
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
      </div>

      {/* Grid content */}
      <div ref={scrollContainerRef} className="min-h-0 flex-1 overflow-y-auto">
        {servicesState.loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="size-10 shrink-0 animate-pulse rounded-lg bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 animate-pulse rounded bg-muted" />
                    <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                  </div>
                </div>
                <div className="border-t border-border/60" />
                <div className="flex gap-3">
                  <div className="h-3 w-14 animate-pulse rounded bg-muted" />
                  <div className="h-3 w-16 animate-pulse rounded bg-muted" />
                  <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        ) : servicesState.services.length === 0 ? (
          <div className="flex flex-col items-center gap-4 py-20">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5">
              <Plug className="size-6 text-primary/60" />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-foreground">
                {searchQuery ? 'No matches found' : 'No services yet'}
              </p>
              <p className="mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">
                {searchQuery
                  ? 'Try a different search term or filter'
                  : 'Create a service to connect a provider with an API key for your agents to use'}
              </p>
            </div>
            {!searchQuery && (
              <CustomButton type="primary" icon={<Plus />} size="sm" onClick={openCreate}>
                Add Service
              </CustomButton>
            )}
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {servicesState.services.map((svc) => (
                <ServiceCard
                  key={svc.uuid}
                  service={svc}
                  onNavigate={() => router.push(`/service-providers/${svc.service_provider_id}`)}
                  onEdit={() => openEdit(svc)}
                  onDelete={() => handleDelete(svc)}
                />
              ))}
            </div>

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="shrink-0">
              {servicesState.loadingMore && (
                <div className="flex items-center justify-center gap-2 py-6">
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Loading more...</span>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      {!servicesState.loading && servicesState.services.length > 0 && (
        <div className="mt-3 text-center text-xs text-muted-foreground">
          {servicesState.services.length} of {total} service{total !== 1 ? 's' : ''}
        </div>
      )}

      {/* Service Modal */}
      <ServiceUpsertModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        service={editingService}
      />
    </div>
  );
}

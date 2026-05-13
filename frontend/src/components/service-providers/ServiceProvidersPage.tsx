'use client';

import { fetchServicesAtom, servicesAtom, upsertServiceAtom } from '@/atoms/ProviderAtom';
import ServiceCard from '@/components/service-providers/ServiceCard';
import ServiceUpsertModal from '@/components/service-providers/ServiceUpsertModal';
import SectionTitle from '@/components/settings/SectionTitle';
import { CustomButton } from '@/components/shared';
import ToneLoader from '@/components/shared/ToneLoader';
import { deleteService as deleteServiceApi } from '@/services/providerService';
import type { Service, ServiceUpsertPayload } from '@/types/provider';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { BrainCircuit, Loader2, Mic, Plug, Plus, Search, Volume2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { SERVICE_TYPE_SECTIONS, SERVICES_PAGE_SIZE } from './constants';

const SECTION_ICONS: Record<string, { icon: React.ElementType; color: string }> = {
  llm: { icon: BrainCircuit, color: 'text-violet-600 dark:text-violet-400' },
  stt: { icon: Mic, color: 'text-sky-600 dark:text-sky-400' },
  tts: { icon: Volume2, color: 'text-amber-600 dark:text-amber-400' },
};

export default function ServiceProvidersPage() {
  const router = useRouter();
  const [servicesState] = useAtom(servicesAtom);
  const [, fetchServices] = useAtom(fetchServicesAtom);
  const [, upsertSvc] = useAtom(upsertServiceAtom);

  const hasFetchedRef = useRef(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);

  // ── Helpers ──────────────────────────────────────────────────────

  const buildParams = useCallback(
    (page: number, nameOverride?: string) => {
      const params: Record<string, unknown> = { page, page_size: SERVICES_PAGE_SIZE };
      const name = nameOverride ?? searchQuery;
      if (name.trim()) params.name = name.trim();
      return params;
    },
    [searchQuery],
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

  // Group services by service_type for the three sections
  const servicesByType = useMemo(() => {
    const groups: Record<string, Service[]> = { llm: [], stt: [], tts: [] };
    for (const svc of servicesState.services) {
      const key = (svc.service_type ?? '').toLowerCase();
      if (key in groups) groups[key].push(svc);
    }
    return groups;
  }, [servicesState.services]);

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

      {/* Toolbar: Search */}
      <div className="mb-4">
        <div className="relative max-w-md">
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
      </div>

      {/* Sections content */}
      <div
        ref={scrollContainerRef}
        className="min-h-0 flex-1 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {servicesState.loading ? (
          <div className="flex h-full items-center justify-center">
            <ToneLoader label="Loading services..." />
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
            {SERVICE_TYPE_SECTIONS.map((section) => {
              const sectionServices = servicesByType[section.key] ?? [];
              if (sectionServices.length === 0) return null;
              const { icon, color } = SECTION_ICONS[section.key];
              return (
                <section key={section.key} className="mb-8">
                  <SectionTitle
                    icon={icon}
                    iconColor={color}
                    title={section.title}
                    count={sectionServices.length}
                  />
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {sectionServices.map((svc) => (
                      <ServiceCard
                        key={svc.uuid}
                        service={svc}
                        onNavigate={() =>
                          router.push(`/service-providers/${svc.service_provider_id}`)
                        }
                        onEdit={() => openEdit(svc)}
                        onDelete={() => handleDelete(svc)}
                      />
                    ))}
                  </div>
                </section>
              );
            })}

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

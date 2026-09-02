'use client';

/**
 * Admin-facing list view for ``app_integrations``.
 *
 * Mirrors the structure of :file:`frontend/src/components/mcp/MCPListPage.tsx`
 * — cards in a responsive grid, each with an :component:`ActionMenu` for
 * edit + delete. Default (seeded) rows are protected: the delete option is
 * hidden so admins can't accidentally remove rows the seed will re-create.
 *
 * Reuses the shared form (`AppIntegrationFormPage`) for both edit (navigates
 * to ``/settings/integrations/edit/{id}``) and create
 * (``/settings/integrations/new``) — this page is a list-and-actions wrapper,
 * not a form.
 */

import { CustomButton } from '@/components/shared';
import { useAppIntegrations, useDeleteAppIntegration } from '@/lib/api/appIntegrations';
import type { AppIntegration } from '@/types/appIntegration';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { ArrowLeft, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect } from 'react';

import IntegrationCard from './IntegrationCard';
import IntegrationsEmptyState from './IntegrationsEmptyState';
import IntegrationsLoadingState from './IntegrationsLoadingState';

export default function AppIntegrationListPage() {
  const router = useRouter();

  // Server list moved into the TanStack cache. ``page_size: 200`` is generous —
  // the catalog will never realistically grow past a few dozen rows.
  const { data: integrations = [], isLoading, error } = useAppIntegrations({ page_size: 200 });
  const { mutateAsync: deleteIntegration } = useDeleteAppIntegration();

  // Preserve the previous toast-on-fetch-error behavior.
  useEffect(() => {
    if (error) handleApiError(error);
  }, [error]);

  const handleEdit = useCallback(
    (integration: AppIntegration) => {
      router.push(`/settings/integrations/edit/${integration.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (integration: AppIntegration) => {
      try {
        // The delete mutation invalidates the list query, so it refreshes.
        await deleteIntegration(integration.id);
        showToast.success(`${integration.display_name} deleted`);
      } catch (err) {
        handleApiError(err);
      }
    },
    [deleteIntegration],
  );

  const goToNew = useCallback(() => router.push('/settings/integrations/new'), [router]);
  const goToIntegrations = useCallback(() => router.push('/settings/integrations'), [router]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Top bar — same shape as the form's top bar for visual consistency. */}
      <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-6 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={goToIntegrations}
            aria-label="Back to integrations"
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
              Manage integrations
            </h1>
            <p className="truncate text-[11.5px] text-muted-foreground">
              Edit or remove the integrations available in your catalog.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <CustomButton type="primary" size="sm" onClick={goToNew} icon={<Plus size={13} />}>
            New integration
          </CustomButton>
        </div>
      </div>

      {/* Body — scrollable grid. */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/30">
        <div className="mx-auto w-full max-w-5xl px-6 py-7">
          {isLoading && integrations.length === 0 ? (
            <IntegrationsLoadingState />
          ) : integrations.length === 0 ? (
            <IntegrationsEmptyState onCreate={goToNew} />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {integrations.map((integration) => (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                  onEdit={() => handleEdit(integration)}
                  onDelete={() => handleDelete(integration)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

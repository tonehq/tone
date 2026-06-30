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

import { ActionMenu, CustomButton } from '@/components/shared';
import { deleteAppIntegration, listAppIntegrations } from '@/services/appIntegrationService';
import type { AppIntegration } from '@/types/appIntegration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { ArrowLeft, KeyRound, Loader2, Plus, ShieldCheck, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

export default function AppIntegrationListPage() {
  const router = useRouter();
  const [integrations, setIntegrations] = useState<AppIntegration[]>([]);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch the full list. Wrapped in ``useCallback`` so post-mutation refreshes
   * (after a delete) don't recreate the function identity unnecessarily.
   * ``page_size: 200`` is generous — the catalog will never realistically grow
   * past a few dozen rows.
   */
  const refresh = useCallback(() => {
    setLoading(true);
    listAppIntegrations({ page_size: 200 })
      .then((res) => setIntegrations(res.rows))
      .catch((err) => handleApiError(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleEdit = useCallback(
    (integration: AppIntegration) => {
      router.push(`/settings/integrations/edit/${integration.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (integration: AppIntegration) => {
      try {
        await deleteAppIntegration(integration.id);
        showToast.success(`${integration.display_name} deleted`);
        refresh();
      } catch (err) {
        handleApiError(err);
      }
    },
    [refresh],
  );

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Top bar — same shape as the form's top bar for visual consistency. */}
      <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-6 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={() => router.push('/settings/integrations')}
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
          <CustomButton
            type="primary"
            size="sm"
            onClick={() => router.push('/settings/integrations/new')}
            icon={<Plus size={13} />}
          >
            New integration
          </CustomButton>
        </div>
      </div>

      {/* Body — scrollable grid. */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/30">
        <div className="mx-auto w-full max-w-5xl px-6 py-7">
          {loading && integrations.length === 0 ? (
            <LoadingState />
          ) : integrations.length === 0 ? (
            <EmptyState onCreate={() => router.push('/settings/integrations/new')} />
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

// ─────────────────────────────────────────────────────────────────────
// Card + states
// ─────────────────────────────────────────────────────────────────────

interface IntegrationCardProps {
  integration: AppIntegration;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

function IntegrationCard({ integration, onEdit, onDelete }: IntegrationCardProps) {
  // Default (seeded) rows are protected by the backend; hiding ``onDelete``
  // makes the menu show only the Edit action so admins don't see a button
  // that would 400.
  const deleteHandler = integration.is_default ? undefined : onDelete;

  return (
    <article
      className="group flex h-full cursor-pointer flex-col rounded-lg border border-border bg-background p-4 transition hover:border-violet-300 hover:shadow-sm"
      onClick={onEdit}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-[13px] font-semibold text-foreground">
              {integration.display_name}
            </h3>
            {integration.is_default && (
              <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-500/10 dark:text-violet-300">
                <ShieldCheck size={10} />
                Default
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
            {integration.slug}
          </p>
        </div>
        {/* Click on the menu shouldn't trigger the card's onClick. */}
        <div onClick={(e) => e.stopPropagation()}>
          {deleteHandler ? (
            <ActionMenu
              onEdit={onEdit}
              onDelete={deleteHandler}
              itemName={integration.display_name}
              deleteDescription={`This removes "${integration.display_name}" from your catalog. Existing OAuth connections will be unlinked but kept. This cannot be undone.`}
            />
          ) : (
            <CustomButton
              type="text"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              aria-label="Edit"
            >
              Edit
            </CustomButton>
          )}
        </div>
      </div>

      {integration.description && (
        <p className="mt-2 line-clamp-2 text-[11.5px] text-muted-foreground">
          {integration.description}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge tone={integration.is_enabled ? 'success' : 'muted'}>
          {integration.is_enabled ? 'Enabled' : 'Disabled'}
        </Badge>
        <Badge tone="default" icon={<KeyRound size={9} />}>
          {integration.auth_type}
        </Badge>
        <Badge tone={integration.has_credentials ? 'success' : 'warning'}>
          {integration.has_credentials ? 'Configured' : 'Not configured'}
        </Badge>
      </div>
    </article>
  );
}

interface BadgeProps {
  tone: 'success' | 'warning' | 'default' | 'muted';
  icon?: React.ReactNode;
  children: React.ReactNode;
}

const BADGE_TONES: Record<BadgeProps['tone'], string> = {
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
  default: 'bg-muted text-muted-foreground',
  muted: 'bg-muted/60 text-muted-foreground',
};

function Badge({ tone, icon, children }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
        BADGE_TONES[tone],
      )}
    >
      {icon}
      {children}
    </span>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-20 text-muted-foreground">
      <Loader2 className="mr-2 size-4 animate-spin" />
      <span className="text-sm">Loading integrations…</span>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-background py-16 text-center">
      <Sparkles className="mx-auto size-6 text-violet-500" />
      <h3 className="mt-3 text-[14px] font-semibold text-foreground">No integrations yet</h3>
      <p className="mt-1 text-[12px] text-muted-foreground">
        Add a third-party provider to start connecting accounts.
      </p>
      <div className="mt-4">
        <CustomButton type="primary" size="sm" onClick={onCreate} icon={<Plus size={13} />}>
          New integration
        </CustomButton>
      </div>
    </div>
  );
}

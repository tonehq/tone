import { ActionMenu, CustomButton } from '@/components/shared';
import type { AppIntegration } from '@/types/appIntegration';
import { KeyRound, ShieldCheck } from 'lucide-react';

import IntegrationBadge from './IntegrationBadge';

interface IntegrationCardProps {
  integration: AppIntegration;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export default function IntegrationCard({ integration, onEdit, onDelete }: IntegrationCardProps) {
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
        <IntegrationBadge tone={integration.is_enabled ? 'success' : 'muted'}>
          {integration.is_enabled ? 'Enabled' : 'Disabled'}
        </IntegrationBadge>
        <IntegrationBadge tone="default" icon={<KeyRound size={9} />}>
          {integration.auth_type}
        </IntegrationBadge>
        <IntegrationBadge tone={integration.has_credentials ? 'success' : 'warning'}>
          {integration.has_credentials ? 'Configured' : 'Not configured'}
        </IntegrationBadge>
      </div>
    </article>
  );
}

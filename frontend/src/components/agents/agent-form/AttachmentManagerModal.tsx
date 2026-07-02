'use client';

import { Check, Search } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';

import AttachmentOAuthPicker from '@/components/agents/agent-form/AttachmentOAuthPicker';
import { CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import type { OAuthConnection } from '@/types/oauth';
import { cn } from '@/utils/cn';

/** One catalog entry the modal shows in its browsable list. Both tools and
 * MCP servers project into this shape via the caller. */
export interface AttachmentManagerOption {
  id: string;
  name: string;
  description?: string | null;
  /** Whether this attachment authenticates via OAuth — when ``true`` the
   * modal reveals an OAuth picker under a selected row. */
  usesOAuth: boolean;
  /** The entity's default OAuth connection (from the Tool/MCP page). Used to
   * label "Use default (…)" in the picker. */
  defaultConnectionId?: string | null;
  /** Optional catalog scoping so the picker only lists matching connections. */
  appIntegrationId?: string | null;
}

interface AttachmentManagerModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  searchPlaceholder: string;
  /** Full catalog. Rows are filtered inside the modal by name/description. */
  options: AttachmentManagerOption[];
  selectedIds: string[];
  /** Sparse map ``{id: connection_id | null}`` — ``null`` = "clear override,
   * fall back to entity default". */
  overrides: Record<string, string | null>;
  connections: OAuthConnection[];
  loading?: boolean;
  /** Icon rendered in each list row (Wrench for tools, Server for MCPs). */
  rowIcon: ReactNode;
  rowIconClassName?: string;
  /** Optional slot shown when the catalog is empty (e.g. "Create a tool"). */
  emptyState?: ReactNode;
  onToggle: (id: string) => void;
  onOverrideChange: (id: string, next: string | null) => void;
}

/** Single modal that owns BOTH the browse/select step and the per-attachment
 * OAuth override — so the user never sees a floating dropdown detached from
 * the row it configures. State is fully controlled by the caller: the modal
 * is a view over the same form state ``ToolsMcpStep`` already tracks, which
 * is why closing the modal doesn't need a "Save" step.
 */
export default function AttachmentManagerModal({
  open,
  onClose,
  title,
  description,
  searchPlaceholder,
  options,
  selectedIds,
  overrides,
  connections,
  loading,
  rowIcon,
  rowIconClassName,
  emptyState,
  onToggle,
  onOverrideChange,
}: AttachmentManagerModalProps) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (o) =>
        o.name.toLowerCase().includes(q) || (o.description?.toLowerCase().includes(q) ?? false),
    );
  }, [options, search]);

  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      width="sm:max-w-xl"
      hideFooter={false}
      footer={null}
      contentClassName="p-0"
    >
      <div className="flex flex-col gap-3 px-6 pb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-1 items-center gap-2 rounded-md border border-border/70 bg-background px-2">
            <Search className="size-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="h-9 border-0 px-0 shadow-none focus-visible:ring-0"
            />
          </div>
          {selectedIds.length > 0 && (
            <Badge variant="secondary" className="h-6 px-2 text-[11px] tabular-nums">
              {selectedIds.length} selected
            </Badge>
          )}
        </div>

        <div className="max-h-[420px] overflow-y-auto pr-1">
          {loading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-muted/40" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/70 py-6 text-center text-xs text-muted-foreground">
              {emptyState ?? (search ? `Nothing matches "${search}".` : 'No results.')}
            </div>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {filtered.map((opt) => {
                const isSelected = selected.has(opt.id);
                return (
                  <li
                    key={opt.id}
                    className={cn(
                      'rounded-lg border p-2.5 transition-colors',
                      isSelected
                        ? 'border-primary/40 bg-primary/[0.04]'
                        : 'border-border/70 hover:bg-muted/40',
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onToggle(opt.id)}
                      className="flex w-full items-start gap-2.5 text-left"
                    >
                      <span
                        className={cn(
                          'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
                          rowIconClassName ?? 'bg-muted ring-border text-muted-foreground',
                        )}
                      >
                        {rowIcon}
                      </span>
                      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <span className="truncate text-sm font-medium text-foreground">
                          {opt.name}
                        </span>
                        {opt.description && (
                          <span className="line-clamp-2 text-xs text-muted-foreground">
                            {opt.description}
                          </span>
                        )}
                      </div>
                      <span
                        className={cn(
                          'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors',
                          isSelected
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'border-border bg-background text-transparent',
                        )}
                      >
                        <Check className="size-3" />
                      </span>
                    </button>
                    {isSelected && opt.usesOAuth && (
                      <AttachmentOAuthPicker
                        overrideConnectionId={overrides[opt.id] ?? null}
                        defaultConnectionId={opt.defaultConnectionId ?? null}
                        connections={connections}
                        appIntegrationId={opt.appIntegrationId ?? null}
                        onChange={(next) => onOverrideChange(opt.id, next)}
                      />
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </CustomModal>
  );
}

'use client';

import { CheckCheck, XCircle } from 'lucide-react';

import type { EvalStatusFilter } from '@/components/knowledge-base/evalsConstants';
import { CustomButton, CustomTooltip } from '@/components/shared';
import { cn } from '@/utils/cn';

interface EvalReviewToolbarProps {
  counts: { total: number; pending: number; approved: number };
  activeFilter: EvalStatusFilter;
  onFilterChange: (filter: EvalStatusFilter) => void;
  onApproveAll: () => void;
  onRejectAll: () => void;
  approvingAll: boolean;
  rejectingAll: boolean;
}

const FILTERS: { key: EvalStatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
];

// The review row that sits directly above the question list: status-filter
// chips (with counts) on the left, bulk approve/reject on the right.
export default function EvalReviewToolbar({
  counts,
  activeFilter,
  onFilterChange,
  onApproveAll,
  onRejectAll,
  approvingAll,
  rejectingAll,
}: EvalReviewToolbarProps) {
  const countFor = (key: EvalStatusFilter) =>
    key === 'all' ? counts.total : key === 'pending' ? counts.pending : counts.approved;

  const busy = approvingAll || rejectingAll;
  const bulkDisabled = counts.total === 0 || busy;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-1.5">
        {FILTERS.map((f) => {
          const active = activeFilter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => onFilterChange(f.key)}
              className={cn(
                'cursor-pointer rounded-full px-3 py-1 text-xs font-medium ring-1 transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
                active
                  ? 'bg-primary/10 text-primary ring-primary/30'
                  : 'bg-muted text-muted-foreground ring-border/60 hover:text-foreground',
              )}
              aria-pressed={active}
            >
              {f.label}
              <span className="ml-1 tabular-nums opacity-70">{countFor(f.key)}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <CustomTooltip content="Approve every question in this version">
          <CustomButton
            type="default"
            size="sm"
            onClick={onApproveAll}
            disabled={bulkDisabled}
            loading={approvingAll}
          >
            <CheckCheck className="mr-1 size-4" />
            Approve all
          </CustomButton>
        </CustomTooltip>
        <CustomTooltip content="Reject (delete) every question in this version">
          <CustomButton
            type="default"
            size="sm"
            onClick={onRejectAll}
            disabled={bulkDisabled}
            loading={rejectingAll}
            className="text-destructive"
          >
            <XCircle className="mr-1 size-4" />
            Reject all
          </CustomButton>
        </CustomTooltip>
      </div>
    </div>
  );
}

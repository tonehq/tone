import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

import { CustomButton, SelectInput } from '@/components/shared';

import { LLM_EVALS_PAGE_SIZE_SELECT_OPTIONS } from './constants';

/** Compact pagination footer shared by every paginated list inside the LLM
 * Evals section (scenarios-in-folder + runs). Mirrors the shape used by the
 * shared ``CustomTable`` (rows-per-page selector + first/prev/current/next/
 * last controls) so pagination feels the same everywhere. Kept local to
 * this feature — the scenarios + runs tables are hand-rolled (not rendered
 * through ``CustomTable``), so its built-in pager isn't available to attach. */
export default function LlmEvalsPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  if (total === 0) return null;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, totalPages);
  const firstItem = (currentPage - 1) * pageSize + 1;
  const lastItem = Math.min(currentPage * pageSize, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3">
      <div className="flex items-center gap-3 text-[13px] text-muted-foreground">
        <span>Rows per page</span>
        <SelectInput
          name="rows-per-page"
          value={String(pageSize)}
          onValueChange={(v) => onPageSizeChange(Number(v))}
          options={LLM_EVALS_PAGE_SIZE_SELECT_OPTIONS}
          size="sm"
          triggerClassName="w-16"
        />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-[13px] text-muted-foreground">
          <span className="font-medium text-foreground">
            {firstItem}
            {' - '}
            {lastItem}
          </span>
          {' of '}
          <span className="font-medium text-foreground">{total}</span>
        </span>
        <div className="flex items-center gap-1.5">
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(1)}
            disabled={currentPage <= 1}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronsLeft className="size-4" />
          </CustomButton>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronLeft className="size-4" />
          </CustomButton>
          <span className="flex h-7 min-w-7 items-center justify-center rounded-lg bg-primary/10 px-2 text-xs font-medium text-primary">
            {currentPage}
          </span>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronRight className="size-4" />
          </CustomButton>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage >= totalPages}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronsRight className="size-4" />
          </CustomButton>
        </div>
      </div>
    </div>
  );
}

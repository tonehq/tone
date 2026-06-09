'use client';

import type {
  ColumnDef,
  FilterFn,
  Row,
  SortingState,
  VisibilityState,
} from '@tanstack/react-table';
import {
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Columns3,
  RefreshCw,
  Rows3,
} from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import { CustomButton } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { DataTable } from '@/components/ui/table';
import type { CustomTableDensity, CustomTableProps } from '@/types/components';
import { cn } from '@/utils/cn';

const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50];

const globalFilterFn: FilterFn<unknown> = (row, _columnId, filterValue) => {
  const q = String(filterValue).toLowerCase();
  return row.getVisibleCells().some((cell) => {
    const val = cell.getValue();
    return val != null && String(val).toLowerCase().includes(q);
  });
};

function CustomTableInner<TRow>({
  columns,
  dataSource,
  rowKey,
  loading = false,
  skeletonRows = 12,
  searchable = false,
  searchPlaceholder = 'Search...',
  searchValue,
  onSearchChange,
  pagination,
  emptyState,
  onRowClick,
  onSortChange,
  className,
  toolbar,
  onRefresh,
  refreshing = false,
  enableDensityToggle = false,
  initialDensity = 'cozy',
  enableColumnVisibility = false,
  title,
  description,
  initialSort = null,
}: CustomTableProps<TRow>) {
  const [sorting, setSorting] = useState<SortingState>(() => {
    if (!initialSort) return [];
    const col = columns.find((c) => (c.dataIndex ?? c.key) === initialSort.field);
    if (!col) return [];
    return [{ id: col.key, desc: initialSort.order === 'desc' }];
  });
  const [internalSearch, setInternalSearch] = useState('');
  const [density, setDensity] = useState<CustomTableDensity>(initialDensity);

  // When `onSearchChange` is supplied the parent owns the search state and the
  // table does NOT filter internally — useful for server-driven search.
  const isSearchControlled = onSearchChange != null;
  const searchTerm = isSearchControlled ? (searchValue ?? '') : internalSearch;
  const globalFilter = isSearchControlled ? '' : internalSearch;

  const paginationConfig = pagination || null;
  const paginationEnabled = pagination !== false;
  const isControlled = paginationConfig != null && typeof paginationConfig.onChange === 'function';

  const [internalPage, setInternalPage] = useState(paginationConfig?.current ?? 1);
  const [internalPageSize, setInternalPageSize] = useState(
    paginationConfig?.pageSize ?? DEFAULT_PAGE_SIZE,
  );

  const currentPage = isControlled ? (paginationConfig.current ?? 1) : internalPage;
  const pageSize = isControlled
    ? (paginationConfig.pageSize ?? DEFAULT_PAGE_SIZE)
    : internalPageSize;
  const pageSizeOptions = paginationConfig?.pageSizeOptions ?? DEFAULT_PAGE_SIZE_OPTIONS;

  const setPage = (page: number) => {
    if (isControlled) {
      paginationConfig.onChange!(page, pageSize);
    }
    setInternalPage(page);
  };

  const setPageSize = (size: number) => {
    if (isControlled) {
      paginationConfig.onChange!(1, size);
    }
    setInternalPageSize(size);
    setInternalPage(1);
  };

  const getRowKey = (record: TRow): string | number => {
    if (typeof rowKey === 'function') return rowKey(record);
    return record[rowKey] as string | number;
  };

  const columnDefs = useMemo<ColumnDef<TRow, unknown>[]>(
    () =>
      columns.map((col): ColumnDef<TRow, unknown> => {
        const hasSorter = !!col.sorter;
        const customSorter = typeof col.sorter === 'function' ? col.sorter : undefined;

        return {
          id: col.key,
          ...(col.dataIndex ? { accessorKey: col.dataIndex } : { accessorFn: () => undefined }),
          header: typeof col.title === 'string' ? col.title : () => col.title,
          cell: col.render
            ? ({ getValue, row }) => col.render!(getValue(), row.original, row.index)
            : ({ getValue }) => {
                const val = getValue();
                return val != null ? String(val) : '-';
              },
          enableSorting: hasSorter,
          ...(customSorter
            ? {
                sortingFn: (rowA: Row<TRow>, rowB: Row<TRow>) =>
                  customSorter(rowA.original, rowB.original),
              }
            : {}),
          meta: {
            align: col.align,
            className: col.className,
            width: col.width,
            label: (typeof col.title === 'string' ? col.title : col.key) as string,
          } as ColumnDef<TRow, unknown>['meta'],
        };
      }),
    [columns],
  );

  // Seed column visibility from `hidden` prop, then let the user toggle.
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(() => {
    const vis: VisibilityState = {};
    for (const col of columns) {
      if (col.hidden) vis[col.key] = false;
    }
    return vis;
  });

  // Re-sync if the consumer flips `hidden` on a column after mount.
  useEffect(() => {
    setColumnVisibility((prev) => {
      const next: VisibilityState = { ...prev };
      for (const col of columns) {
        if (col.hidden) next[col.key] = false;
      }
      return next;
    });
  }, [columns]);

  const table = useReactTable<TRow>({
    data: dataSource,
    columns: columnDefs,
    state: {
      sorting,
      globalFilter,
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    onSortingChange: (updater) => {
      const next = typeof updater === 'function' ? updater(sorting) : updater;
      setSorting(next);
      if (onSortChange) {
        if (next.length > 0) {
          const { id, desc } = next[0];
          const col = columns.find((c) => c.key === id);
          const field = col?.dataIndex ?? id;
          onSortChange({ field, order: desc ? 'desc' : 'asc' });
        } else {
          onSortChange(null);
        }
      }
    },
    onGlobalFilterChange: (value: string) => {
      if (!isSearchControlled) setInternalSearch(value);
    },
    globalFilterFn: globalFilterFn as FilterFn<TRow>,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableSortingRemoval: true,
  });

  const processedRows = table.getRowModel().rows;
  const isServerPaginated = paginationConfig?.total != null;
  const totalItems = paginationConfig?.total ?? processedRows.length;
  const totalPages = paginationEnabled ? Math.max(1, Math.ceil(totalItems / pageSize)) : 1;
  const paginatedRows =
    paginationEnabled && !isServerPaginated
      ? processedRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)
      : processedRows;

  // Has any toolbar content been requested?
  const hasToolbar =
    searchable ||
    !!toolbar ||
    !!onRefresh ||
    enableDensityToggle ||
    enableColumnVisibility ||
    !!title ||
    !!description;

  return (
    <div className={cn('flex flex-col gap-4 min-h-0', className)}>
      {(title || description) && (
        <div className="flex flex-col gap-1">
          {title && <h3 className="text-base font-semibold tracking-tight">{title}</h3>}
          {description && <p className="text-[13px] text-muted-foreground">{description}</p>}
        </div>
      )}

      {hasToolbar && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-1 items-center gap-2 min-w-0">
            {searchable && (
              <SearchBar
                value={searchTerm}
                placeholder={searchPlaceholder}
                // Server-driven search debounces; in-memory search fires on every
                // keystroke so the filter feels instant.
                debounceMs={isSearchControlled ? 300 : 0}
                onSearch={(v) => {
                  if (isSearchControlled) {
                    // The parent's params setter is expected to reset to page 1
                    // when search changes — so we don't fire a second write here.
                    onSearchChange!(v);
                  } else {
                    setInternalSearch(v);
                    setPage(1);
                  }
                }}
                containerClassName="max-w-xs"
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            {toolbar}
            {onRefresh && (
              <CustomButton
                type="default"
                size="icon-sm"
                onClick={() => onRefresh()}
                disabled={refreshing}
                aria-label="Refresh"
              >
                <RefreshCw
                  className={cn('size-4 text-muted-foreground', refreshing && 'animate-spin')}
                />
              </CustomButton>
            )}
            {enableDensityToggle && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <CustomButton type="default" size="icon-sm" aria-label="Row density">
                    <Rows3 className="size-4 text-muted-foreground" />
                  </CustomButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-44">
                  <DropdownMenuLabel className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    Density
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuRadioGroup
                    value={density}
                    onValueChange={(v) => setDensity(v as CustomTableDensity)}
                  >
                    <DropdownMenuRadioItem value="compact">Compact</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="cozy">Cozy</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="comfortable">Comfortable</DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            {enableColumnVisibility && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <CustomButton type="default" size="icon-sm" aria-label="Toggle columns">
                    <Columns3 className="size-4 text-muted-foreground" />
                  </CustomButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  <DropdownMenuLabel className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    Columns
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {table.getAllLeafColumns().map((col) => (
                    <DropdownMenuCheckboxItem
                      key={col.id}
                      checked={col.getIsVisible()}
                      onCheckedChange={(value) => col.toggleVisibility(!!value)}
                      onSelect={(e) => e.preventDefault()}
                    >
                      {((col.columnDef.meta as { label?: string })?.label as string) ?? col.id}
                    </DropdownMenuCheckboxItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-col min-h-0 overflow-hidden rounded-2xl border border-border/70 bg-card">
        <DataTable
          table={table}
          rows={paginatedRows}
          loading={loading}
          skeletonRows={skeletonRows}
          emptyState={emptyState}
          onRowClick={onRowClick}
          getRowKey={getRowKey}
          density={density}
        />

        {paginationEnabled && !loading && processedRows.length > 0 && (
          <div className="flex items-center justify-between border-t border-border px-5 py-3.5">
            <div className="flex items-center gap-3 text-[13px] text-muted-foreground">
              <span>Rows per page</span>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="h-8 w-16 cursor-pointer rounded-lg border border-input bg-background px-2 text-[13px] text-foreground transition-colors hover:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
              >
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-[13px] text-muted-foreground">
                <span className="font-medium text-foreground">
                  {(currentPage - 1) * pageSize + 1}
                  {' - '}
                  {Math.min(currentPage * pageSize, totalItems)}
                </span>
                {' of '}
                <span className="font-medium text-foreground">{totalItems}</span>
              </span>
              <div className="flex items-center gap-1.5">
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={() => setPage(1)}
                  disabled={currentPage <= 1}
                  className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ChevronsLeft className="size-4" />
                </CustomButton>
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={() => setPage(currentPage - 1)}
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
                  onClick={() => setPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ChevronRight className="size-4" />
                </CustomButton>
                <CustomButton
                  type="text"
                  size="icon-xs"
                  onClick={() => setPage(totalPages)}
                  disabled={currentPage >= totalPages}
                  className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ChevronsRight className="size-4" />
                </CustomButton>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const CustomTable = React.memo(CustomTableInner) as typeof CustomTableInner;

export default CustomTable;

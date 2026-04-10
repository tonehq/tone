'use client';

import { CustomButton, TextInput } from '@/components/shared';
import { DataTable } from '@/components/ui/table';
import type { CustomTableProps } from '@/types/components';
import { cn } from '@/utils/cn';
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
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Search } from 'lucide-react';
import React, { useMemo, useState } from 'react';

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
  pagination,
  emptyState,
  onRowClick,
  className,
}: CustomTableProps<TRow>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

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
      columns
        .filter((col) => !col.hidden)
        .map((col): ColumnDef<TRow, unknown> => {
          const hasSorter = !!col.sorter;
          const customSorter = typeof col.sorter === 'function' ? col.sorter : undefined;

          return {
            id: col.key,
            ...(col.dataIndex ? { accessorKey: col.dataIndex } : { accessorFn: () => undefined }),
            header: col.title,
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
            },
          };
        }),
    [columns],
  );

  const columnVisibility = useMemo<VisibilityState>(() => {
    const vis: VisibilityState = {};
    for (const col of columns) {
      if (col.hidden) {
        vis[col.key] = false;
      }
    }
    return vis;
  }, [columns]);

  const table = useReactTable<TRow>({
    data: dataSource,
    columns: columnDefs,
    state: {
      sorting,
      globalFilter,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: globalFilterFn as FilterFn<TRow>,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableSortingRemoval: true,
  });

  const processedRows = table.getRowModel().rows;
  const totalItems = paginationConfig?.total ?? processedRows.length;
  const totalPages = paginationEnabled ? Math.max(1, Math.ceil(totalItems / pageSize)) : 1;
  const paginatedRows = paginationEnabled
    ? processedRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : processedRows;

  return (
    <div className={cn('flex flex-col gap-5 min-h-0', className)}>
      {searchable && (
        <div className="max-w-xs">
          <TextInput
            name="table-search"
            placeholder={searchPlaceholder}
            value={globalFilter}
            onChange={(e) => {
              setGlobalFilter(e.target.value);
              setPage(1);
            }}
            leftIcon={<Search className="size-4" />}
          />
        </div>
      )}

      <div className="flex flex-col min-h-0 overflow-hidden rounded-md border border-border bg-card shadow-sm">
        <DataTable
          table={table}
          rows={paginatedRows}
          loading={loading}
          skeletonRows={skeletonRows}
          emptyState={emptyState}
          onRowClick={onRowClick}
          getRowKey={getRowKey}
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

'use client';

import { CustomButton, TextInput } from '@/components/shared';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { CustomTableColumn, CustomTableProps } from '@/types/components';
import { cn } from '@/utils/cn';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
} from 'lucide-react';
import React, { useMemo, useState } from 'react';

export type {
  CustomTableColumn,
  CustomTablePagination,
  CustomTableProps
} from '@/types/components';

const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50];

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  columnKey: string | null;
  direction: SortDirection;
}

function CustomTableInner<TRow>({
  columns,
  dataSource,
  rowKey,
  loading = false,
  skeletonRows = 5,
  searchable = false,
  searchPlaceholder = 'Search...',
  pagination,
  emptyState,
  onRowClick,
  className,
}: CustomTableProps<TRow>) {
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortState>({ columnKey: null, direction: null });
  const [internalPage, setInternalPage] = useState(1);
  const [internalPageSize, setInternalPageSize] = useState(DEFAULT_PAGE_SIZE);

  const paginationEnabled = pagination !== false;
  const isControlled = paginationEnabled && pagination != null;

  const currentPage = isControlled ? pagination.current : internalPage;
  const pageSize = isControlled ? pagination.pageSize : internalPageSize;
  const pageSizeOptions = isControlled
    ? (pagination.pageSizeOptions ?? DEFAULT_PAGE_SIZE_OPTIONS)
    : DEFAULT_PAGE_SIZE_OPTIONS;

  const setPage = (page: number) => {
    if (isControlled) {
      pagination.onChange?.(page, pageSize);
    } else {
      setInternalPage(page);
    }
  };

  const setPageSize = (size: number) => {
    if (isControlled) {
      pagination.onChange?.(1, size);
    } else {
      setInternalPageSize(size);
      setInternalPage(1);
    }
  };

  const getRowKey = (record: TRow): string | number => {
    if (typeof rowKey === 'function') return rowKey(record);
    return record[rowKey] as string | number;
  };

  const visibleColumns = useMemo(() => columns.filter((col) => !col.hidden), [columns]);

  const filteredData = useMemo(() => {
    if (!search.trim()) return dataSource;
    const q = search.toLowerCase();
    return dataSource.filter((row) =>
      visibleColumns.some((col) => {
        if (!col.dataIndex) return false;
        const val = row[col.dataIndex];
        return val != null && String(val).toLowerCase().includes(q);
      }),
    );
  }, [dataSource, search, visibleColumns]);

  const sortedData = useMemo(() => {
    if (!sort.columnKey || !sort.direction) return filteredData;
    const col = columns.find((c) => c.key === sort.columnKey);
    if (!col) return filteredData;

    const dir = sort.direction === 'asc' ? 1 : -1;

    const { sorter } = col;
    if (typeof sorter === 'function') {
      return [...filteredData].sort((a, b) => sorter(a, b) * dir);
    }

    if (!col.dataIndex) return filteredData;
    const key = col.dataIndex;
    return [...filteredData].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') return (aVal - bVal) * dir;
      return String(aVal).localeCompare(String(bVal)) * dir;
    });
  }, [filteredData, sort, columns]);

  const totalItems =
    isControlled && pagination.total != null ? pagination.total : sortedData.length;
  const totalPages = paginationEnabled ? Math.max(1, Math.ceil(totalItems / pageSize)) : 1;
  const paginatedData = paginationEnabled
    ? sortedData.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : sortedData;

  const handleSort = (columnKey: string) => {
    setSort((prev) => {
      if (prev.columnKey !== columnKey) return { columnKey, direction: 'asc' };
      if (prev.direction === 'asc') return { columnKey, direction: 'desc' };
      return { columnKey: null, direction: null };
    });
  };

  const alignClass = (align?: 'left' | 'center' | 'right') => {
    if (align === 'center') return 'text-center';
    if (align === 'right') return 'text-right';
    return 'text-left';
  };

  const getCellValue = (col: CustomTableColumn<TRow>, row: TRow, index: number) => {
    const rawValue = col.dataIndex ? row[col.dataIndex] : undefined;
    if (col.render) return col.render(rawValue, row, index);
    return rawValue != null ? String(rawValue) : '-';
  };

  return (
    <div className={cn('flex flex-col gap-5', className)}>
      {searchable && (
        <div className="max-w-xs">
          <TextInput
            name="table-search"
            placeholder={searchPlaceholder}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            leftIcon={<Search className="size-4" />}
          />
        </div>
      )}

      <div className="rounded-md border border-border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-border bg-muted/40 hover:bg-muted/40">
              {visibleColumns.map((col) => (
                <TableHead
                  key={col.key}
                  className={cn(
                    'h-11 px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground',
                    alignClass(col.align),
                    col.sorter &&
                      'cursor-pointer select-none transition-colors hover:text-foreground',
                    col.width,
                    col.className,
                  )}
                  onClick={col.sorter ? () => handleSort(col.key) : undefined}
                >
                  <span className="inline-flex items-center gap-1.5">
                    {col.title}
                    {col.sorter && (
                      <span className="inline-flex">
                        {sort.columnKey === col.key && sort.direction === 'asc' ? (
                          <ArrowUp className="size-3.5 text-foreground" />
                        ) : sort.columnKey === col.key && sort.direction === 'desc' ? (
                          <ArrowDown className="size-3.5 text-foreground" />
                        ) : (
                          <ArrowUpDown className="size-3.5 opacity-30" />
                        )}
                      </span>
                    )}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? (
              Array.from({ length: skeletonRows }).map((_, i) => (
                <TableRow key={`skeleton-${i}`} className="border-b border-border/50">
                  {visibleColumns.map((col) => (
                    <TableCell
                      key={col.key}
                      className={cn('px-4 py-3.5', alignClass(col.align), col.width)}
                    >
                      <div className="h-4 w-3/4 animate-pulse rounded-md bg-muted/80" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : paginatedData.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={visibleColumns.length} className="h-56 text-center">
                  {emptyState ?? (
                    <span className="text-sm text-muted-foreground">No results found.</span>
                  )}
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, index) => (
                <TableRow
                  key={getRowKey(row)}
                  className={cn(
                    'border-b border-border/50 transition-colors hover:bg-muted/20',
                    onRowClick && 'cursor-pointer',
                  )}
                  onClick={
                    onRowClick
                      ? (e) => {
                          const target = e.target as HTMLElement;
                          if (
                            target.closest?.('[data-slot="dialog-portal"]') ||
                            target.closest?.('[role="dialog"]')
                          )
                            return;
                          onRowClick(row, index);
                        }
                      : undefined
                  }
                >
                  {visibleColumns.map((col) => (
                    <TableCell
                      key={col.key}
                      className={cn(
                        'px-4 py-3.5 text-sm',
                        alignClass(col.align),
                        col.width,
                        col.className,
                      )}
                    >
                      {getCellValue(col, row, index)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {paginationEnabled && !loading && sortedData.length > 0 && (
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

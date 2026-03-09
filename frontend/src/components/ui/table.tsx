'use client';

import * as React from 'react';

import { cn } from '@/utils/cn';
import type { Row as TanStackRow, Table as TanStackTable } from '@tanstack/react-table';
import { flexRender } from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';

declare module '@tanstack/react-table' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-unnecessary-type-constraint
  interface ColumnMeta<TData extends unknown, TValue> {
    align?: 'left' | 'center' | 'right';
    className?: string;
    width?: string;
  }
}

function alignClass(align?: 'left' | 'center' | 'right') {
  if (align === 'center') return 'text-center';
  if (align === 'right') return 'text-right';
  return 'text-left';
}

/* -------------------------------------------------------------------------- */
/*  Base primitives (shadcn)                                                  */
/* -------------------------------------------------------------------------- */

function Table({ className, ...props }: React.ComponentProps<'table'>) {
  return (
    <div data-slot="table-container" className="relative w-full flex-1 overflow-auto">
      <table
        data-slot="table"
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return <thead data-slot="table-header" className={cn('[&_tr]:border-b', className)} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return (
    <tbody
      data-slot="table-body"
      className={cn('[&_tr:last-child]:border-0', className)}
      {...props}
    />
  );
}

function TableFooter({ className, ...props }: React.ComponentProps<'tfoot'>) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn('bg-muted/50 border-t font-medium [&>tr]:last:border-b-0', className)}
      {...props}
    />
  );
}

function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        'hover:bg-muted/50 data-[state=selected]:bg-muted border-b transition-colors',
        className,
      )}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        'text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
        className,
      )}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        'p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
        className,
      )}
      {...props}
    />
  );
}

function TableCaption({ className, ...props }: React.ComponentProps<'caption'>) {
  return (
    <caption
      data-slot="table-caption"
      className={cn('text-muted-foreground mt-4 text-sm', className)}
      {...props}
    />
  );
}

/* -------------------------------------------------------------------------- */
/*  DataTable — TanStack-powered rendering                                    */
/* -------------------------------------------------------------------------- */

interface DataTableProps<TData> {
  table: TanStackTable<TData>;
  rows?: TanStackRow<TData>[];
  loading?: boolean;
  skeletonRows?: number;
  emptyState?: React.ReactNode;
  onRowClick?: (record: TData, index: number) => void;
  getRowKey?: (record: TData) => string | number;
}

function DataTableInner<TData>(
  {
    table,
    rows,
    loading = false,
    skeletonRows = 10,
    emptyState,
    onRowClick,
    getRowKey,
  }: DataTableProps<TData>,
  _ref: React.Ref<HTMLTableElement>,
) {
  const displayRows = rows ?? table.getRowModel().rows;
  const headerGroup = table.getHeaderGroups()[0];
  const visibleColumns = table.getVisibleLeafColumns();

  return (
    <Table>
      <TableHeader className="sticky top-0 z-10 bg-card">
        <TableRow className="border-b border-border bg-muted/40 hover:bg-muted/40">
          {headerGroup.headers.map((header) => {
            const meta = header.column.columnDef.meta;
            const canSort = header.column.getCanSort();
            return (
              <TableHead
                key={header.id}
                className={cn(
                  'h-11 px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground',
                  alignClass(meta?.align),
                  canSort && 'cursor-pointer select-none transition-colors hover:text-foreground',
                  meta?.width,
                  meta?.className,
                )}
                onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
              >
                <span className="inline-flex items-center gap-1.5">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {canSort && (
                    <span className="inline-flex">
                      {header.column.getIsSorted() === 'asc' ? (
                        <ArrowUp className="size-3.5 text-foreground" />
                      ) : header.column.getIsSorted() === 'desc' ? (
                        <ArrowDown className="size-3.5 text-foreground" />
                      ) : (
                        <ArrowUpDown className="size-3.5 opacity-30" />
                      )}
                    </span>
                  )}
                </span>
              </TableHead>
            );
          })}
        </TableRow>
      </TableHeader>

      <TableBody>
        {loading ? (
          Array.from({ length: skeletonRows }).map((_, i) => (
            <TableRow key={`skeleton-${i}`} className="border-b border-border/50">
              {visibleColumns.map((col) => (
                <TableCell
                  key={col.id}
                  className={cn(
                    'px-4 py-3.5',
                    alignClass(col.columnDef.meta?.align),
                    col.columnDef.meta?.width,
                  )}
                >
                  <div className="h-4 w-3/4 animate-pulse rounded-md bg-muted/80" />
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : displayRows.length === 0 ? (
          <TableRow className="hover:bg-transparent">
            <TableCell colSpan={visibleColumns.length} className="h-56 text-center">
              {emptyState ?? (
                <span className="text-sm text-muted-foreground">No results found.</span>
              )}
            </TableCell>
          </TableRow>
        ) : (
          displayRows.map((row) => (
            <TableRow
              key={getRowKey ? getRowKey(row.original) : row.id}
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
                      onRowClick(row.original, row.index);
                    }
                  : undefined
              }
            >
              {row.getVisibleCells().map((cell) => {
                const meta = cell.column.columnDef.meta;
                return (
                  <TableCell
                    key={cell.id}
                    className={cn(
                      'px-4 py-3.5 text-sm',
                      alignClass(meta?.align),
                      meta?.width,
                      meta?.className,
                    )}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                );
              })}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

const DataTable = React.forwardRef(DataTableInner) as <TData>(
  props: DataTableProps<TData> & { ref?: React.Ref<HTMLTableElement> },
) => React.ReactElement;

export {
  DataTable,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
};
export type { DataTableProps };

'use client';

import * as React from 'react';

import { cn } from '@/utils/cn';
import type { Row as TanStackRow, Table as TanStackTable } from '@tanstack/react-table';
import { flexRender } from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown, SearchX } from 'lucide-react';

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
    <div data-slot="table-container" className="relative w-full overflow-auto">
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

type TableDensity = 'compact' | 'cozy' | 'comfortable';

const DENSITY_CELL_CLASS: Record<TableDensity, string> = {
  compact: 'px-3 py-2.5',
  cozy: 'px-4 py-4',
  comfortable: 'px-5 py-[1.35rem]',
};

interface DataTableProps<TData> {
  table: TanStackTable<TData>;
  rows?: TanStackRow<TData>[];
  loading?: boolean;
  skeletonRows?: number;
  emptyState?: React.ReactNode;
  onRowClick?: (record: TData, index: number) => void;
  getRowKey?: (record: TData) => string | number;
  density?: TableDensity;
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
    density = 'cozy',
  }: DataTableProps<TData>,
  _ref: React.Ref<HTMLTableElement>,
) {
  const cellPadding = DENSITY_CELL_CLASS[density];
  const displayRows = rows ?? table.getRowModel().rows;
  const headerGroup = table.getHeaderGroups()[0];
  const visibleColumns = table.getVisibleLeafColumns();

  return (
    <Table>
      <TableHeader className="sticky top-0 z-10 bg-card">
        <TableRow className="border-b border-border hover:bg-transparent">
          {headerGroup.headers.map((header) => {
            const meta = header.column.columnDef.meta;
            const canSort = header.column.getCanSort();
            const sorted = header.column.getIsSorted();
            return (
              <TableHead
                key={header.id}
                className={cn(
                  'h-12 px-4 text-[11px] font-semibold uppercase tracking-[0.11em] text-muted-foreground/80',
                  'first:pl-6 last:pr-6',
                  alignClass(meta?.align),
                  canSort && 'cursor-pointer select-none transition-colors hover:text-foreground',
                  sorted && 'text-foreground',
                  meta?.width,
                  meta?.className,
                )}
                onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
              >
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5',
                    meta?.align === 'right' && 'flex-row-reverse',
                  )}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {canSort && (
                    <span className="inline-flex">
                      {sorted === 'asc' ? (
                        <ArrowUp className="size-3 text-foreground" />
                      ) : sorted === 'desc' ? (
                        <ArrowDown className="size-3 text-foreground" />
                      ) : (
                        <ArrowUpDown className="size-3 opacity-25" />
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
            <TableRow key={`skeleton-${i}`} className="border-b border-border/40 last:border-0">
              {visibleColumns.map((col) => (
                <TableCell
                  key={col.id}
                  className={cn(
                    cellPadding,
                    'first:pl-6 last:pr-6',
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
          <TableRow className="hover:bg-transparent hover:shadow-none">
            <TableCell colSpan={visibleColumns.length} className="h-56 text-center">
              {emptyState ?? (
                <div className="flex flex-col items-center justify-center gap-3 py-6">
                  <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-background">
                    <SearchX className="size-5 text-muted-foreground/60" strokeWidth={1.75} />
                  </span>
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground/60">
                    No results found
                  </span>
                </div>
              )}
            </TableCell>
          </TableRow>
        ) : (
          displayRows.map((row) => (
            <TableRow
              key={getRowKey ? getRowKey(row.original) : row.id}
              className={cn(
                'border-b border-border/50 transition-colors duration-150 last:border-0',
                'hover:bg-muted/40',
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
                      cellPadding,
                      'text-sm text-foreground first:pl-6 last:pr-6',
                      meta?.align === 'right' && 'tabular-nums',
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

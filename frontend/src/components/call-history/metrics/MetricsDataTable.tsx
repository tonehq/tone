import { cn } from '@/utils/cn';
import React from 'react';

export interface MetricsTableColumn<T> {
  key: string;
  header: React.ReactNode;
  align?: 'left' | 'right';
  /** Optional fixed cell width — Tailwind class (e.g. `w-12`). */
  width?: string;
  cell: (row: T, index: number) => React.ReactNode;
}

interface MetricsDataTableProps<T> {
  columns: MetricsTableColumn<T>[];
  rows: T[];
  getRowKey?: (row: T, index: number) => React.Key;
  emptyMessage?: string;
  className?: string;
}

/**
 * Shared, column-def driven table for metric sections. Styled to match the
 * cards/borders used by the rest of the metrics page so chart→table swaps
 * stay visually consistent.
 *
 * Each section defines its own typed column list; this component owns the
 * markup so we don't repeat `<table>/<thead>/<tbody>` styling per section.
 */
export function MetricsDataTable<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage = 'No data',
  className,
}: MetricsDataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <div className={cn('overflow-hidden rounded-lg border border-border', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  'px-3 py-2 text-xs font-medium text-muted-foreground',
                  col.align === 'right' ? 'text-right' : 'text-left',
                  col.width,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={getRowKey?.(row, i) ?? i} className="border-b border-border last:border-0">
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    'px-3 py-2 tabular-nums text-foreground',
                    col.align === 'right' ? 'text-right' : 'text-left',
                  )}
                >
                  {col.cell(row, i)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

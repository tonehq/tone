'use client';

import { CustomTable } from '@/components/shared';
import type {
  CustomTableColumn,
  CustomTablePagination,
  CustomTableSortState,
} from '@/types/components';

/**
 * A thin wrapper over the shared `CustomTable` preset for contact-style rows, wired for
 * SERVER-side search / sort / pagination.
 *
 * WHAT: forwards a controlled search value, server sort state, and a server-total
 * pagination config to `CustomTable`, so a paginated contacts endpoint drives it directly.
 * Callers supply the `columns` (so the directory General view, the Agent Contacts tab,
 * and the Assign picker can each render their own action/checkbox columns) and the row
 * data for the current page.
 *
 * WHEN: use for every contacts listing that talks to a `POST /…/list` endpoint via
 * `usePaginatedList` — pass the page's params state + setter down so search/sort/page
 * changes flow back to the query. Do NOT re-implement CustomTable wiring per screen.
 */
export interface ContactsTableProps<TRow> {
  columns: CustomTableColumn<TRow>[];
  data: TRow[];
  rowKey: (keyof TRow & string) | ((record: TRow) => string | number);
  loading?: boolean;
  /** Total row count from the server envelope (`total`) — enables server pagination. */
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number, pageSize: number) => void;
  /** Controlled search term (server-driven). Omit both to disable the search box. */
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Current server sort, reflected in the header; `onSortChange` sends the new sort up. */
  sort?: CustomTableSortState | null;
  onSortChange?: (sort: CustomTableSortState | null) => void;
  emptyState?: React.ReactNode;
  onRowClick?: (record: TRow, index: number) => void;
  /** Extra toolbar content (e.g. Add / Sync / bulk-delete buttons). */
  toolbar?: React.ReactNode;
  className?: string;
  /**
   * Grow the table card to fill its parent's height (body scrolls internally, pagination
   * pinned at the card bottom). Parent must be a bounded `flex flex-col`. Optional,
   * back-compatible — defaults to `false` so existing callers (Agent Contacts tab,
   * Assign picker) keep their auto-height layout.
   */
  fillHeight?: boolean;
  /** Tag rows with `group` so cells can reveal actions on hover/focus. Optional. */
  groupRows?: boolean;
}

export default function ContactsTable<TRow>({
  columns,
  data,
  rowKey,
  loading = false,
  total,
  page,
  pageSize,
  onPageChange,
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search contacts...',
  sort,
  onSortChange,
  emptyState,
  onRowClick,
  toolbar,
  className,
  fillHeight = false,
  groupRows = false,
}: ContactsTableProps<TRow>) {
  const pagination: CustomTablePagination = {
    current: page,
    pageSize,
    total,
    onChange: onPageChange,
  };

  return (
    <CustomTable<TRow>
      columns={columns}
      dataSource={data}
      rowKey={rowKey}
      loading={loading}
      searchable={onSearchChange != null}
      searchValue={searchValue}
      onSearchChange={onSearchChange}
      searchPlaceholder={searchPlaceholder}
      pagination={pagination}
      initialSort={sort ?? null}
      onSortChange={onSortChange}
      emptyState={emptyState}
      onRowClick={onRowClick}
      toolbar={toolbar}
      className={className}
      fillHeight={fillHeight}
      groupRows={groupRows}
    />
  );
}

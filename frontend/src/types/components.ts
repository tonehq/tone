export interface CustomTableColumn<TRow> {
  key: string;
  title: string;
  dataIndex?: keyof TRow & string;
  render?: (value: unknown, record: TRow, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  sorter?: boolean | ((a: TRow, b: TRow) => number);
  className?: string;
  width?: string;
  hidden?: boolean;
}

export interface CustomTablePagination {
  current: number;
  pageSize: number;
  total?: number;
  pageSizeOptions?: number[];
  onChange?: (page: number, pageSize: number) => void;
}

export interface CustomTableProps<TRow> {
  columns: CustomTableColumn<TRow>[];
  dataSource: TRow[];
  rowKey: (keyof TRow & string) | ((record: TRow) => string | number);
  loading?: boolean;
  skeletonRows?: number;
  searchable?: boolean;
  searchPlaceholder?: string;
  pagination?: CustomTablePagination | false;
  emptyState?: React.ReactNode;
  onRowClick?: (record: TRow, index: number) => void;
  className?: string;
}

export interface CustomModalProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode | null;
  confirmText?: string;
  cancelText?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
  confirmLoading?: boolean;
  confirmType?: 'primary' | 'danger';
  confirmDisabled?: boolean;
  hideFooter?: boolean;
  width?: string;
  className?: string;
  showCloseButton?: boolean;
}

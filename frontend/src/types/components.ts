export interface CustomTableColumn<TRow> {
  key: string;
  title: string | React.ReactNode;
  dataIndex?: keyof TRow & string;
  render?: (value: unknown, record: TRow, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  sorter?: boolean | ((a: TRow, b: TRow) => number);
  className?: string;
  width?: string;
  hidden?: boolean;
}

export interface CustomTablePagination {
  current?: number;
  pageSize?: number;
  total?: number;
  pageSizeOptions?: number[];
  onChange?: (page: number, pageSize: number) => void;
}

export interface CustomTableSortState {
  field: string;
  order: 'asc' | 'desc';
}

export type CustomTableDensity = 'compact' | 'cozy' | 'comfortable';

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
  onSortChange?: (sort: CustomTableSortState | null) => void;
  className?: string;
  /** Custom toolbar content rendered to the right of the search bar. */
  toolbar?: React.ReactNode;
  /** Show a refresh button in the toolbar — calls back when clicked. */
  onRefresh?: () => void | Promise<void>;
  /** Whether the refresh button shows a spinner. */
  refreshing?: boolean;
  /** Show a density (compact/cozy/comfortable) toggle in the toolbar. */
  enableDensityToggle?: boolean;
  /** Initial density when the toggle is enabled. */
  initialDensity?: CustomTableDensity;
  /** Show a column-visibility menu in the toolbar. */
  enableColumnVisibility?: boolean;
  /** Title displayed above the toolbar (small, optional). */
  title?: React.ReactNode;
  /** Description displayed under the title. */
  description?: React.ReactNode;
}

export interface TextInputBaseProps extends Omit<React.ComponentProps<'input'>, 'size'> {
  name?: string;
  type?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  leftIcon?: React.ReactNode;
}

export interface FormTextInputProps
  extends Omit<TextInputBaseProps, 'value' | 'onChange' | 'onBlur' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: string) => void;
}

export interface CheckboxFieldBaseProps
  extends Omit<React.ComponentProps<'button'>, 'id' | 'checked' | 'defaultChecked'> {
  id: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
}

export interface FormCheckboxFieldProps
  extends Omit<CheckboxFieldBaseProps, 'checked' | 'onCheckedChange' | 'ref'> {
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onCheckedChange?: (checked: boolean) => void;
}

export interface RadioGroupFieldBaseProps
  extends Omit<
    React.ComponentProps<'div'>,
    'aria-invalid' | 'aria-required' | 'defaultValue' | 'dir'
  > {
  name: string;
  label?: string;
  options: RadioGroupOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  orientation?: 'horizontal' | 'vertical';
  disabled?: boolean;
}

export interface RadioGroupOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface FormRadioGroupFieldProps
  extends Omit<RadioGroupFieldBaseProps, 'value' | 'onValueChange' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: string) => void;
  transformValue?: (value: string) => unknown;
}

export interface SelectInputBaseProps {
  name: string;
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  className?: string;
  triggerClassName?: string;
  size?: 'sm' | 'default';
  position?: 'item-aligned' | 'popper';
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface FormSelectInputProps
  extends Omit<SelectInputBaseProps, 'value' | 'onValueChange' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: string) => void;
}

export interface TextAreaFieldBaseProps extends Omit<React.ComponentProps<'textarea'>, 'size'> {
  name: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
}

export interface FormTextAreaFieldProps
  extends Omit<TextAreaFieldBaseProps, 'value' | 'onChange' | 'onBlur' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: string) => void;
}

export interface MultiSelectOption {
  value: string;
  label: string;
}

export interface MultiSelectFieldBaseProps {
  name: string;
  options?: MultiSelectOption[];
  value?: string[];
  onChange?: (value: string[]) => void;
  placeholder?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  className?: string;
  disabled?: boolean;
}

export interface FormMultiSelectFieldProps
  extends Omit<MultiSelectFieldBaseProps, 'value' | 'onChange' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onChange?: (value: string[]) => void;
}

export interface SliderFieldBaseProps {
  name: string;
  value?: number;
  onValueChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  className?: string;
  disabled?: boolean;
  showLabels?: boolean;
}

export interface FormSliderFieldProps
  extends Omit<SliderFieldBaseProps, 'value' | 'onValueChange' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: number) => void;
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
  contentClassName?: string;
  showCloseButton?: boolean;
}

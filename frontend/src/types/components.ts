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
  /** Controlled search value — pair with onSearchChange to drive search externally. */
  searchValue?: string;
  /** When provided, the search input becomes controlled and no internal filtering happens. */
  onSearchChange?: (value: string) => void;
  pagination?: CustomTablePagination | false;
  emptyState?: React.ReactNode;
  onRowClick?: (record: TRow, index: number) => void;
  onSortChange?: (sort: CustomTableSortState | null) => void;
  /** Seeds the table's sort state on first render so the header reflects a
   * server-side default. The page is still responsible for sending the
   * matching `sort_by` value on its initial request. */
  initialSort?: CustomTableSortState | null;
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
  /** Optional custom renderer for each option row — lets callers render rich
   * content (icons, two-line rows) in the list. Falls back to the plain string
   * `label` when omitted. The string `label` is still used as the Radix
   * typeahead / accessible text value. */
  renderOption?: (option: SelectOption) => React.ReactNode;
  /** Optional custom renderer for the selected value shown in the trigger.
   * Receives the current value; falls back to the default text when omitted. */
  renderValue?: (value: string | undefined) => React.ReactNode;
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
  autoResize?: boolean;
}

export interface FormTextAreaFieldProps
  extends Omit<TextAreaFieldBaseProps, 'value' | 'onChange' | 'onBlur' | 'ref'> {
  name: string;
  control: import('react-hook-form').Control<any>;
  rules?: import('react-hook-form').RegisterOptions;
  onValueChange?: (value: string) => void;
}

export interface RichPromptEditorFieldBaseProps {
  name: string;
  label?: string;
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  isRequired?: boolean;
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  labelClassName?: string;
  className?: string;
  id?: string;
  /** Min height of the editing surface, e.g. '220px'. */
  minHeight?: string;
  /** Max height of the editing surface; beyond it the editor scrolls internally
   * (e.g. '60vh'). Without it the editor grows to fit its content. */
  maxHeight?: string;
  /** Fill the parent's height (the editor area flex-grows and scrolls internally,
   * so the surrounding page doesn't scroll). The parent chain must be height-bounded. */
  fill?: boolean;
}

export interface FormRichPromptEditorFieldProps
  extends Omit<RichPromptEditorFieldBaseProps, 'value' | 'onChange'> {
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

export interface CustomDrawerProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode | null;
  side?: 'left' | 'right' | 'top' | 'bottom';
  width?: string;
  className?: string;
  contentClassName?: string;
  showCloseButton?: boolean;
}

/**
 * Emitted value of the shared {@link DateRangePicker}. `start`/`end` are UTC ISO
 * instants (or null when cleared); `timeZone` is the IANA zone the user picked
 * the wall-clock time in (defaults to the browser zone).
 */
export interface DateRangeValue {
  start: string | null;
  end: string | null;
  timeZone: string;
}

export interface DateRangePickerProps {
  value?: DateRangeValue;
  onChange?: (value: DateRangeValue) => void;
  placeholder?: string;
  /** Show the relative-range preset rail (Last 15m / 30m / 1h / 24h / 7d). */
  presets?: boolean;
  align?: 'start' | 'center' | 'end';
  className?: string;
  triggerClassName?: string;
  disabled?: boolean;
}

/** A single `field:value` token in the {@link TokenSearchBar}. */
export interface SearchToken {
  field: string;
  value: string;
}

/** Field definition consumed by {@link TokenSearchBar}. */
export interface TokenSearchField {
  key: string;
  label: string;
  /** `enum` fields autocomplete from `fetchValues`; `text` fields accept free input. */
  type?: 'enum' | 'text';
  /** Lazily fetch distinct values for an `enum` field (cached after first load). */
  fetchValues?: () => Promise<string[]>;
  /** Map a stored value to its display label (defaults to the raw value). */
  formatValue?: (value: string) => string;
}

export interface TokenSearchBarProps {
  fields: TokenSearchField[];
  value: SearchToken[];
  onChange: (tokens: SearchToken[]) => void;
  placeholder?: string;
  className?: string;
  /** Hide the inline chips (e.g. when applied filters are shown in a separate row). */
  hideChips?: boolean;
  /** Render a trailing "clear" control inside the bar; called when clicked. */
  onClear?: () => void;
  /** Force-show the clear control. Defaults to showing whenever there are tokens. */
  showClear?: boolean;
}

export interface CustomPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * Radix modal mode. Enable when the popover has its own scrollable content and
   * lives inside another scroll-locking layer (e.g. a Drawer/Sheet) — modal gives
   * the popover its own scroll lock so wheel/trackpad scrolling works inside it.
   */
  modal?: boolean;
  /** The element that toggles the popover. Rendered with Radix `asChild`. */
  trigger: React.ReactNode;
  title?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode | null;
  align?: 'start' | 'center' | 'end';
  side?: 'top' | 'right' | 'bottom' | 'left';
  sideOffset?: number;
  /** Tailwind width class (defaults to `w-60`). */
  width?: string;
  className?: string;
  contentClassName?: string;
  /**
   * Extra props forwarded directly to the underlying Radix `PopoverContent`.
   * Use this to attach `id`, `aria-*`, `data-testid`, or the Radix focus /
   * dismissal handlers (`onOpenAutoFocus`, `onCloseAutoFocus`,
   * `onEscapeKeyDown`, `onInteractOutside`, `onPointerDownOutside`, etc).
   */
  contentProps?: Omit<React.HTMLAttributes<HTMLDivElement>, 'className' | 'children'> & {
    onOpenAutoFocus?: (event: Event) => void;
    onCloseAutoFocus?: (event: Event) => void;
    onEscapeKeyDown?: (event: KeyboardEvent) => void;
    onInteractOutside?: (event: Event) => void;
    onPointerDownOutside?: (event: PointerEvent) => void;
    avoidCollisions?: boolean;
    collisionPadding?: number | Partial<Record<'top' | 'right' | 'bottom' | 'left', number>>;
  };
}

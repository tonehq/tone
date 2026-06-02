'use client';

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/utils/cn';
import { CheckIcon, ChevronDownIcon, SearchIcon } from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';

import { Label } from '@/components/ui/label';

export interface SearchableSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SearchableSelectProps<T extends SearchableSelectOption> {
  name: string;
  options: T[];
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  label?: string;
  isRequired?: boolean;
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  renderOption?: (option: T, isSelected: boolean) => ReactNode;
  renderSelectedValue?: (option: T) => ReactNode;
  filterFn?: (option: T, query: string) => boolean;
  emptyMessage?: string;
  className?: string;
}

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
);

function defaultFilter<T extends SearchableSelectOption>(option: T, query: string): boolean {
  return option.label.toLowerCase().includes(query.toLowerCase());
}

function SearchableSelectInner<T extends SearchableSelectOption>(
  {
    name,
    options,
    value,
    onValueChange,
    placeholder = 'Select an option',
    searchPlaceholder = 'Search...',
    label,
    isRequired = false,
    loading = false,
    disabled = false,
    error = false,
    helperText,
    renderOption,
    renderSelectedValue,
    filterFn,
    emptyMessage = 'No results found.',
    className,
  }: SearchableSelectProps<T>,
  ref: React.ForwardedRef<HTMLButtonElement>,
) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filter = filterFn ?? defaultFilter;
  const filtered = search ? options.filter((o) => filter(o, search)) : options;
  const selectedOption = options.find((o) => o.value === value);

  // Reset search and highlight when popover opens/closes
  useEffect(() => {
    if (open) {
      setSearch('');
      setHighlightIndex(-1);
      // Focus search input after popover animation
      requestAnimationFrame(() => {
        searchInputRef.current?.focus();
      });
    }
  }, [open]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIndex < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll('[data-option-index]');
    items[highlightIndex]?.scrollIntoView({ block: 'nearest' });
  }, [highlightIndex]);

  const handleSelect = useCallback(
    (optionValue: string) => {
      onValueChange?.(optionValue);
      setOpen(false);
    },
    [onValueChange],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightIndex((prev) => (prev > 0 ? prev - 1 : filtered.length - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (highlightIndex >= 0 && highlightIndex < filtered.length) {
          const opt = filtered[highlightIndex];
          if (!opt.disabled) handleSelect(opt.value);
        }
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    },
    [filtered, highlightIndex, handleSelect],
  );

  if (loading) {
    return (
      <div className="mb-2">
        {label && <Skeleton className="mb-1 h-4 w-20" />}
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  return (
    <div className={className}>
      {label && (
        <Label htmlFor={name} className="mb-1.5">
          {label}
          {isRequired && <span className="ml-0.5 text-destructive">*</span>}
        </Label>
      )}

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            ref={ref}
            type="button"
            id={name}
            role="combobox"
            aria-expanded={open}
            aria-controls={open ? `${name}-listbox` : undefined}
            aria-invalid={error || undefined}
            disabled={disabled}
            className={cn(
              "border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 dark:hover:bg-input/50 flex w-full items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 h-9 overflow-hidden",
              error &&
                'border-destructive focus-visible:border-destructive focus-visible:ring-destructive/50',
            )}
          >
            <span className="min-w-0 flex-1 overflow-hidden">
              {selectedOption ? (
                renderSelectedValue ? (
                  renderSelectedValue(selectedOption)
                ) : (
                  selectedOption.label
                )
              ) : (
                <span className="text-muted-foreground">{placeholder}</span>
              )}
            </span>
            <ChevronDownIcon className="size-4 shrink-0 opacity-50" />
          </button>
        </PopoverTrigger>

        <PopoverContent
          onKeyDown={handleKeyDown}
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="max-h-80 overflow-hidden"
        >
          {/* Search input */}
          <div className="flex items-center gap-2 border-b px-3 py-0.5">
            <SearchIcon className="size-4 shrink-0 text-muted-foreground/70" />
            <input
              ref={searchInputRef}
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setHighlightIndex(-1);
              }}
              placeholder={searchPlaceholder}
              className="flex h-9 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>

          {/* Options list */}
          <div
            ref={listRef}
            role="listbox"
            id={`${name}-listbox`}
            className="max-h-64 overflow-y-auto p-1"
          >
            {filtered.length === 0 ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </div>
            ) : (
              filtered.map((option, index) => {
                const isSelected = option.value === value;
                return (
                  <div
                    key={option.value}
                    role="option"
                    aria-selected={isSelected}
                    data-option-index={index}
                    data-disabled={option.disabled || undefined}
                    className={cn(
                      'relative flex w-full cursor-default items-center rounded-md px-2 py-2 text-sm outline-hidden select-none transition-colors',
                      'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
                      highlightIndex === index && 'bg-accent text-accent-foreground',
                      !option.disabled && 'cursor-pointer',
                    )}
                    onMouseEnter={() => setHighlightIndex(index)}
                    onClick={() => {
                      if (!option.disabled) handleSelect(option.value);
                    }}
                  >
                    {renderOption ? (
                      renderOption(option, isSelected)
                    ) : (
                      <>
                        <span className="flex-1">{option.label}</span>
                        {isSelected && <CheckIcon className="ml-2 size-4 shrink-0" />}
                      </>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </PopoverContent>
      </Popover>

      {helperText && (
        <p className={cn('mt-1 text-xs', error ? 'text-destructive' : 'text-muted-foreground')}>
          {helperText}
        </p>
      )}
    </div>
  );
}

const SearchableSelect = React.memo(React.forwardRef(SearchableSelectInner)) as <
  T extends SearchableSelectOption,
>(
  props: SearchableSelectProps<T> & { ref?: React.Ref<HTMLButtonElement> },
) => React.ReactElement | null;

export default SearchableSelect;

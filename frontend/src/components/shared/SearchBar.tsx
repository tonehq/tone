'use client';

import { Search, X } from 'lucide-react';
import React, { forwardRef, useEffect, useRef, useState } from 'react';

import { cn } from '@/utils/cn';

export interface SearchBarProps
  extends Omit<React.ComponentProps<'input'>, 'type' | 'value' | 'defaultValue' | 'onChange'> {
  /** Controlled value — when provided the input mirrors it. */
  value?: string;
  /** Initial value for uncontrolled mode. */
  defaultValue?: string;
  /** Fires on every keystroke (use for snappy local UI updates). */
  onChange?: (value: string) => void;
  /** Fires after `debounceMs` of inactivity (use for API calls). */
  onSearch?: (value: string) => void;
  /** Debounce delay in milliseconds — default 300. */
  debounceMs?: number;
  /** Show an X button that clears the input. */
  clearable?: boolean;
  containerClassName?: string;
}

/**
 * Shared search input with built-in debounce.
 *
 *   <SearchBar onSearch={(q) => fetch(q)} />            // 300ms debounce
 *   <SearchBar value={q} onSearch={...} debounceMs={0} />// no debounce
 */
const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(
  (
    {
      value: controlledValue,
      defaultValue = '',
      onChange,
      onSearch,
      debounceMs = 300,
      placeholder = 'Search...',
      clearable = true,
      containerClassName,
      className,
      ...rest
    },
    ref,
  ) => {
    const isControlled = controlledValue !== undefined;
    const [internal, setInternal] = useState(isControlled ? (controlledValue ?? '') : defaultValue);

    // Keep internal state in sync when the parent updates the controlled prop.
    useEffect(() => {
      if (isControlled && controlledValue !== internal) {
        setInternal(controlledValue ?? '');
      }
    }, [controlledValue, isControlled]);

    // Debounce the onSearch callback. We track the last value emitted so we
    // don't fire when the user briefly types and reverts to the same query.
    const lastEmittedRef = useRef<string>(isControlled ? (controlledValue ?? '') : defaultValue);
    useEffect(() => {
      if (!onSearch) return;
      if (debounceMs <= 0) {
        if (internal !== lastEmittedRef.current) {
          lastEmittedRef.current = internal;
          onSearch(internal);
        }
        return;
      }
      const timer = setTimeout(() => {
        if (internal !== lastEmittedRef.current) {
          lastEmittedRef.current = internal;
          onSearch(internal);
        }
      }, debounceMs);
      return () => clearTimeout(timer);
    }, [internal, onSearch, debounceMs]);

    const handleInput = (event: React.ChangeEvent<HTMLInputElement>) => {
      const next = event.target.value;
      setInternal(next);
      onChange?.(next);
    };

    const handleClear = () => {
      setInternal('');
      onChange?.('');
      // Fire onSearch immediately on clear — users expect instant reset.
      lastEmittedRef.current = '';
      onSearch?.('');
    };

    const showClear = clearable && internal.length > 0;

    return (
      <div className={cn('relative w-full max-w-sm', containerClassName)}>
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          ref={ref}
          type="search"
          value={internal}
          onChange={handleInput}
          placeholder={placeholder}
          className={cn(
            'h-9 w-full rounded-lg border border-border bg-background pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring',
            // Hide the native clear button — we render our own.
            '[&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-decoration]:appearance-none',
            className,
          )}
          {...rest}
        />
        {showClear && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>
    );
  },
);

SearchBar.displayName = 'SearchBar';

export default React.memo(SearchBar);

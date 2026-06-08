'use client';

import { Search, X } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { TokenSearchBarProps, TokenSearchField } from '@/types/components';
import { cn } from '@/utils/cn';

export type { SearchToken, TokenSearchBarProps, TokenSearchField } from '@/types/components';

interface Suggestion {
  kind: 'field' | 'value' | 'hint';
  key: string;
  label: string;
}

/**
 * Tokenized `field:value` search bar with autocomplete chips (Vercel-style).
 * Typing shows the field list; picking a field fetches its values (for `enum`
 * fields) and shows a value list; confirmed filters render as removable chips.
 * Emits a normalized `SearchToken[]`.
 */
const TokenSearchBar: React.FC<TokenSearchBarProps> = ({
  fields,
  value,
  onChange,
  placeholder = 'Filter by field… (e.g. status:completed)',
  className,
  hideChips = false,
  onClear,
  showClear,
}) => {
  const [query, setQuery] = useState('');
  const [activeField, setActiveField] = useState<TokenSearchField | null>(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [valuesCache, setValuesCache] = useState<Record<string, string[]>>({});
  const [loadingValues, setLoadingValues] = useState(false);
  const [liveMsg, setLiveMsg] = useState('');

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fieldByKey = useMemo(() => new Map(fields.map((f) => [f.key, f])), [fields]);

  // Close the dropdown when clicking outside the component.
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      // A node already detached by a re-render (e.g. an option we just replaced)
      // is not a genuine outside click — ignore it so the panel stays open.
      if (!document.contains(target)) return;
      if (containerRef.current && !containerRef.current.contains(target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  // Lazily load + cache distinct values for the active enum field.
  useEffect(() => {
    if (!activeField || activeField.type === 'text' || !activeField.fetchValues) return;
    if (valuesCache[activeField.key]) return;
    let cancelled = false;
    setLoadingValues(true);
    activeField
      .fetchValues()
      .then((vals) => {
        if (!cancelled) setValuesCache((p) => ({ ...p, [activeField.key]: vals }));
      })
      .catch(() => {
        if (!cancelled) setValuesCache((p) => ({ ...p, [activeField.key]: [] }));
      })
      .finally(() => {
        if (!cancelled) setLoadingValues(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeField, valuesCache]);

  // Typing "status:" auto-activates that field (matches the chip syntax).
  useEffect(() => {
    if (activeField) return;
    const m = query.match(/^([a-zA-Z_]+):$/);
    if (m) {
      const f = fieldByKey.get(m[1].toLowerCase());
      if (f) {
        setActiveField(f);
        setQuery('');
      }
    }
  }, [query, activeField, fieldByKey]);

  const suggestions = useMemo<Suggestion[]>(() => {
    const q = query.trim().toLowerCase();
    if (!activeField) {
      return fields
        .filter((f) => f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q))
        .map((f) => ({ kind: 'field', key: f.key, label: f.label }));
    }
    if (activeField.type === 'text') {
      return q ? [{ kind: 'hint', key: query.trim(), label: query.trim() }] : [];
    }
    const all = valuesCache[activeField.key] ?? [];
    const taken = new Set(value.filter((t) => t.field === activeField.key).map((t) => t.value));
    return all
      .filter((v) => !taken.has(v) && v.toLowerCase().includes(q))
      .map((v) => ({
        kind: 'value',
        key: v,
        label: activeField.formatValue ? activeField.formatValue(v) : v,
      }));
  }, [activeField, query, fields, valuesCache, value]);

  // Reset the highlight whenever the visible list changes.
  useEffect(() => setHighlight(0), [activeField, query, open]);

  const isLoadingActiveValues =
    !!activeField && activeField.type !== 'text' && loadingValues && !valuesCache[activeField.key];

  const addToken = useCallback(
    (field: string, raw: string) => {
      const val = raw.trim();
      if (!val) return;
      if (!value.some((t) => t.field === field && t.value === val)) {
        onChange([...value, { field, value: val }]);
        setLiveMsg(`Added filter ${field} ${val}`);
      }
      setActiveField(null);
      setQuery('');
      // Keep the panel open (showing the field list) so the user can chain
      // filters; don't rely on a focus event, which won't fire if the input
      // never lost focus during the controlled re-render.
      setOpen(true);
      inputRef.current?.focus();
    },
    [value, onChange],
  );

  const removeToken = useCallback(
    (index: number) => {
      const removed = value[index];
      onChange(value.filter((_, i) => i !== index));
      if (removed) setLiveMsg(`Removed filter ${removed.field} ${removed.value}`);
    },
    [value, onChange],
  );

  const selectSuggestion = useCallback(
    (s: Suggestion) => {
      if (s.kind === 'field') {
        const f = fieldByKey.get(s.key);
        if (f) {
          setActiveField(f);
          setQuery('');
          // Force the panel open for the value list — focus() alone won't
          // re-open it when the input is already focused.
          setOpen(true);
          inputRef.current?.focus();
        }
      } else if (activeField) {
        addToken(activeField.key, s.key);
      }
    },
    [activeField, addToken, fieldByKey],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const s = suggestions[highlight];
      if (s) selectSuggestion(s);
      else if (activeField && activeField.type === 'text' && query.trim())
        addToken(activeField.key, query);
    } else if (e.key === 'Escape') {
      setOpen(false);
    } else if (e.key === 'Backspace' && query === '') {
      if (activeField) setActiveField(null);
      else if (value.length) removeToken(value.length - 1);
    }
  };

  const showDropdown =
    open &&
    (isLoadingActiveValues ||
      suggestions.length > 0 ||
      (!!activeField && activeField.type !== 'text'));

  const showClearButton = !!onClear && (showClear ?? value.length > 0);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div
        className="flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1 shadow-xs transition-colors focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/30"
        onClick={() => inputRef.current?.focus()}
      >
        <Search className="size-4 shrink-0 text-muted-foreground" />

        {!hideChips &&
          value.map((t, i) => {
            const f = fieldByKey.get(t.field);
            const fieldLabel = f?.label ?? t.field;
            const valueLabel = f?.formatValue ? f.formatValue(t.value) : t.value;
            return (
              <span
                key={`${t.field}-${t.value}-${i}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 py-1 pl-2.5 pr-1 text-xs"
              >
                <span className="text-muted-foreground">{fieldLabel}</span>
                <span className="max-w-[160px] truncate font-medium text-foreground">
                  {valueLabel}
                </span>
                <button
                  type="button"
                  aria-label={`Remove ${fieldLabel} ${valueLabel}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeToken(i);
                  }}
                  className="inline-flex size-4 cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-foreground/10 hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              </span>
            );
          })}

        {activeField && (
          <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            {activeField.label}
          </span>
        )}

        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          role="combobox"
          aria-expanded={showDropdown}
          aria-controls="token-search-listbox"
          aria-autocomplete="list"
          aria-label="Filter call history"
          placeholder={
            value.length === 0 && !activeField ? placeholder : activeField ? 'Value…' : ''
          }
          className="h-7 min-w-[140px] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />

        {showClearButton && (
          <button
            type="button"
            aria-label="Clear all filters"
            title="Clear all filters"
            onMouseDown={(e) => e.preventDefault()}
            onClick={(e) => {
              e.stopPropagation();
              setActiveField(null);
              setQuery('');
              setOpen(false);
              onClear?.();
            }}
            className="ml-auto inline-flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {showDropdown && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border border-border bg-popover shadow-md">
          <div className="border-b border-border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {activeField ? `${activeField.label} value` : 'Filters'}
          </div>
          <div id="token-search-listbox" role="listbox" className="max-h-60 overflow-y-auto p-1">
            {isLoadingActiveValues ? (
              <div className="px-2 py-2 text-sm text-muted-foreground">Loading…</div>
            ) : suggestions.length === 0 ? (
              <div className="px-2 py-2 text-sm text-muted-foreground">No matches</div>
            ) : (
              suggestions.map((s, i) => (
                <div
                  key={`${s.kind}-${s.key}`}
                  role="option"
                  aria-selected={i === highlight}
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    selectSuggestion(s);
                  }}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm text-foreground',
                    i === highlight && 'bg-accent',
                  )}
                >
                  {s.kind === 'field' && (
                    <span className="font-mono text-xs text-muted-foreground">{s.key}:</span>
                  )}
                  {s.kind === 'hint' ? (
                    <span className="text-muted-foreground">
                      Add{' '}
                      <span className="font-mono text-foreground">{`${activeField?.key}:${s.label}`}</span>
                    </span>
                  ) : (
                    <span className="truncate">{s.label}</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <span className="sr-only" aria-live="polite">
        {liveMsg}
      </span>
    </div>
  );
};

export default React.memo(TokenSearchBar);

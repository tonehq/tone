'use client';

import { Checkbox } from '@/components/ui/checkbox';
import type { FacetOptionListProps, FacetValue } from '@/types/facetedList';
import { cn } from '@/utils/cn';
import { Search } from 'lucide-react';
import React, { useMemo, useState } from 'react';

import { titleCase } from './utils';

/** Searchable checkbox list of facet values with per-value counts. */
const FacetOptionList: React.FC<FacetOptionListProps> = ({
  field,
  label,
  titleCase: useTitleCase,
  values,
  selected,
  loading,
  onToggle,
}) => {
  const [query, setQuery] = useState('');
  const format = (v: string) => (useTitleCase ? titleCase(v) : v);

  const options = useMemo<FacetValue[]>(() => {
    const present = new Set(values.map((v) => v.value));
    // Keep selected-but-absent values visible (count 0) so they can be unchecked.
    const extra = selected.filter((s) => !present.has(s)).map((s) => ({ value: s, count: 0 }));
    return [...values, ...extra];
  }, [values, selected]);

  const showSearch = options.length > 8;
  const filtered = query
    ? options.filter((o) => format(o.value).toLowerCase().includes(query.toLowerCase()))
    : options;

  const isLoading = loading && values.length === 0;

  return (
    <>
      {showSearch && (
        <div className="mb-2 flex items-center gap-2 rounded-md border border-input bg-background px-2">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${label.toLowerCase()}…`}
            aria-label={`Search ${label}`}
            className="h-7 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
      )}

      <div className="flex max-h-56 flex-col gap-0.5 overflow-y-auto">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2.5 px-2 py-1.5">
              <div className="size-3.5 animate-pulse rounded bg-muted" />
              <div className="h-3.5 flex-1 animate-pulse rounded bg-muted" />
            </div>
          ))
        ) : filtered.length === 0 ? (
          <p className="px-2 py-1.5 text-[13px] text-muted-foreground">No values</p>
        ) : (
          filtered.map((o) => {
            const checkboxId = `facet-${field}-${o.value}`;
            const isSelected = selected.includes(o.value);
            return (
              <label
                key={o.value}
                htmlFor={checkboxId}
                className={cn(
                  'flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50',
                  isSelected && 'bg-primary/5',
                )}
              >
                <Checkbox
                  id={checkboxId}
                  checked={isSelected}
                  onCheckedChange={() => onToggle(field, o.value)}
                  className="size-3.5"
                />
                <span
                  className={cn(
                    'flex-1 truncate text-[13px] text-foreground',
                    o.count === 0 && !isSelected && 'opacity-50',
                  )}
                >
                  {format(o.value)}
                </span>
                <span className="text-xs tabular-nums text-muted-foreground">{o.count}</span>
              </label>
            );
          })
        )}
      </div>
    </>
  );
};

export default FacetOptionList;

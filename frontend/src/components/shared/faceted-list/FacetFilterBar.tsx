'use client';

import CustomButton from '@/components/shared/CustomButton';
import TokenSearchBar from '@/components/shared/TokenSearchBar';
import { Badge } from '@/components/ui/badge';
import type { SearchToken, TokenSearchField } from '@/types/components';
import { SlidersHorizontal } from 'lucide-react';
import React from 'react';

export interface FacetFilterBarProps {
  fields: TokenSearchField[];
  tokens: SearchToken[];
  onTokensChange: (tokens: SearchToken[]) => void;
  onClear?: () => void;
  showClear?: boolean;
  drawerFilterCount: number;
  onOpenDrawer: () => void;
  placeholder?: string;
  /** Injected to the right of the search bar (e.g. a sort select for card grids). */
  rightSlot?: React.ReactNode;
  /** Hide the Filters button (e.g. when an entity exposes no facets). */
  hideFilters?: boolean;
}

/**
 * Toolbar pairing the tokenized search bar (free-text + facet chips) with a
 * "Filters" drawer trigger (the drawer carries the facet checkboxes +
 * server-driven counts). Optionally renders a `rightSlot` — used by card grids
 * for a sort select.
 */
const FacetFilterBar: React.FC<FacetFilterBarProps> = ({
  fields,
  tokens,
  onTokensChange,
  onClear,
  showClear,
  drawerFilterCount,
  onOpenDrawer,
  placeholder,
  rightSlot,
  hideFilters = false,
}) => (
  <div className="flex flex-wrap items-center gap-2">
    <TokenSearchBar
      fields={fields}
      value={tokens}
      onChange={onTokensChange}
      onClear={onClear}
      showClear={showClear}
      placeholder={placeholder}
      className="min-w-[240px] flex-1"
    />
    {rightSlot}
    {!hideFilters && (
      <CustomButton
        type="default"
        size="sm"
        icon={<SlidersHorizontal className="size-4" />}
        onClick={onOpenDrawer}
        aria-label="Open filters"
        className={
          drawerFilterCount > 0
            ? 'border-primary/40 bg-primary/5 text-foreground hover:bg-primary/10'
            : undefined
        }
      >
        Filters
        {drawerFilterCount > 0 && (
          <Badge className="ml-2 bg-primary/15 text-primary tabular-nums hover:bg-primary/15">
            {drawerFilterCount}
          </Badge>
        )}
      </CustomButton>
    )}
  </div>
);

export default FacetFilterBar;

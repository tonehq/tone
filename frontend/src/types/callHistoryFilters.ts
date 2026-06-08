import type { ReactNode } from 'react';

import type { CallFacets, FacetValue } from '@/types/callLog';
import type { DateRangeValue } from '@/types/components';

/** Config for one faceted (checkbox) filter field. */
export interface FacetSectionConfig {
  field: string;
  label: string;
  /** Title-case the values for display (e.g. `in_progress` → `In Progress`). */
  titleCase?: boolean;
}

/** The full applied/draft filter state for the Call History page. */
export interface CallFilterState {
  dateRange: DateRangeValue;
  /** facet field → selected values */
  facets: Record<string, string[]>;
  minTurns: string;
  maxTurns: string;
  latency: [number, number];
}

/** Shared checkbox-list of facet values (with counts + search), used by the
 * drawer sections and the toolbar quick-filter dropdowns. */
export interface FacetOptionListProps {
  field: string;
  label: string;
  titleCase?: boolean;
  values: FacetValue[];
  selected: string[];
  loading: boolean;
  onToggle: (field: string, value: string) => void;
}

/** Collapsible section inside the filter drawer. */
export interface FilterSectionProps {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** A faceted checkbox section inside the drawer (FilterSection + FacetOptionList). */
export interface FacetSectionProps {
  field: string;
  label: string;
  titleCase?: boolean;
  values: FacetValue[];
  selected: string[];
  loading: boolean;
  onToggle: (field: string, value: string) => void;
}

export interface CallHistoryFilterDrawerProps {
  open: boolean;
  onClose: () => void;
  value: CallFilterState;
  facets: CallFacets;
  facetsLoading: boolean;
  onApply: (next: CallFilterState) => void;
}

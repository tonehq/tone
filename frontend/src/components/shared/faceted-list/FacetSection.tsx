'use client';

import type { FacetSectionProps } from '@/types/facetedList';
import React from 'react';

import FacetOptionList from './FacetOptionList';
import FilterSection from './FilterSection';

/** A faceted checkbox section rendered inside the drawer. */
const FacetSection: React.FC<FacetSectionProps> = ({
  field,
  label,
  titleCase,
  formatValue,
  values,
  selected,
  loading,
  onToggle,
}) => (
  <FilterSection title={label} count={selected.length} defaultOpen={selected.length > 0}>
    <FacetOptionList
      field={field}
      label={label}
      titleCase={titleCase}
      formatValue={formatValue}
      values={values}
      selected={selected}
      loading={loading}
      onToggle={onToggle}
    />
  </FilterSection>
);

export default FacetSection;

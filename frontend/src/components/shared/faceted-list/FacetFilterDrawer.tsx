'use client';

import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';
import type { FacetFilterDrawerProps } from '@/types/facetedList';
import React, { useEffect, useState } from 'react';

import FacetSection from './FacetSection';
import { countFacetFilters } from './utils';

/**
 * Config-driven filter drawer: renders a checkbox facet section per
 * `FacetSectionConfig`, with server-driven counts. Edits live in a local draft
 * until the user clicks Apply (mirrors the Call History drawer).
 */
const FacetFilterDrawer: React.FC<FacetFilterDrawerProps> = ({
  open,
  onClose,
  title = 'Filters',
  description,
  sections,
  value,
  facets,
  facetsLoading,
  onApply,
  extraSections,
}) => {
  const [draft, setDraft] = useState<Record<string, string[]>>(value);

  // Re-seed the draft from the applied value every time the drawer opens.
  useEffect(() => {
    if (open) setDraft(value);
  }, [open, value]);

  const toggleFacet = (field: string, val: string) => {
    setDraft((prev) => {
      const current = prev[field] ?? [];
      const next = current.includes(val) ? current.filter((v) => v !== val) : [...current, val];
      const draftNext = { ...prev };
      if (next.length) draftNext[field] = next;
      else delete draftNext[field];
      return draftNext;
    });
  };

  const handleReset = () => setDraft({});

  const handleApply = () => {
    onApply(draft);
    onClose();
  };

  const activeCount = countFacetFilters(draft);

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      side="right"
      width="w-full sm:max-w-[420px]"
      contentClassName="px-6 pb-6"
      footer={
        <div className="flex items-center justify-between gap-2">
          <CustomButton type="text" size="sm" onClick={handleReset} disabled={activeCount === 0}>
            Reset
          </CustomButton>
          <CustomButton type="primary" size="sm" onClick={handleApply}>
            Apply
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col">
        {sections.map((s) => (
          <FacetSection
            key={s.field}
            field={s.field}
            label={s.label}
            titleCase={s.titleCase}
            formatValue={s.formatValue}
            values={facets[s.field] ?? []}
            selected={draft[s.field] ?? []}
            loading={facetsLoading}
            onToggle={toggleFacet}
          />
        ))}
        {extraSections}
      </div>
    </CustomDrawer>
  );
};

export default FacetFilterDrawer;

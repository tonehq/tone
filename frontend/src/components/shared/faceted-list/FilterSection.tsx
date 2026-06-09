'use client';

import CustomButton from '@/components/shared/CustomButton';
import type { FilterSectionProps } from '@/types/facetedList';
import { cn } from '@/utils/cn';
import { ChevronDown } from 'lucide-react';
import React, { useState } from 'react';

/** Collapsible drawer section with a CustomButton disclosure header. */
const FilterSection: React.FC<FilterSectionProps> = ({
  title,
  count = 0,
  defaultOpen = true,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-border last:border-0">
      <CustomButton
        type="text"
        size="sm"
        fullWidth
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="group h-auto justify-start gap-2 px-0 py-3 hover:bg-transparent"
      >
        <ChevronDown
          className={cn(
            'size-4 shrink-0 text-muted-foreground transition-[transform,color] group-hover:text-foreground',
            !open && '-rotate-90',
          )}
        />
        <span className="text-sm font-medium text-foreground">{title}</span>
        {count > 0 && (
          <span className="ml-auto rounded-full bg-primary/15 px-1.5 text-[11px] font-medium tabular-nums text-primary">
            {count}
          </span>
        )}
      </CustomButton>
      {open && <div className="pb-3">{children}</div>}
    </div>
  );
};

export default FilterSection;

'use client';

import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';

interface ApiRequestSectionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

/** Collapsible config section (icon + title + one-line description), keyboard-operable. */
const ApiRequestSection: React.FC<ApiRequestSectionProps> = ({
  title,
  description,
  icon,
  defaultOpen = false,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-muted/20">
      <CustomButton
        type="text"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="h-auto w-full items-center justify-start gap-2.5 rounded-none px-3 py-2.5 text-left hover:bg-muted/40"
      >
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground ring-1 ring-inset ring-border">
          {icon}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] font-medium text-foreground">{title}</span>
          <span className="block truncate text-[11px] text-muted-foreground">{description}</span>
        </span>
        <ChevronDown
          className={cn(
            'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
            open && 'rotate-180',
          )}
        />
      </CustomButton>
      {open && <div className="flex flex-col gap-3 border-t border-border p-3">{children}</div>}
    </div>
  );
};

export default ApiRequestSection;

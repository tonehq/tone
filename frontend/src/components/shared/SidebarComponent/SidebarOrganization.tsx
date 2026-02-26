'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/utils/cn';
import { ChevronDown } from 'lucide-react';

const WORKSPACE_LABEL = 'My Workspace';

export interface SidebarOrganizationProps {
  isExpanded: boolean;
}

export function SidebarOrganization({ isExpanded }: SidebarOrganizationProps) {
  if (isExpanded) {
    return (
      <button
        type="button"
        className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 transition-all duration-200 hover:bg-white/[0.08]"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.12] text-[13px] font-semibold text-white/90">
          M
        </div>
        <span className="flex-1 truncate text-left text-[13px] font-medium text-white/90">
          {WORKSPACE_LABEL}
        </span>
        <ChevronDown size={14} className="shrink-0 text-white/40" />
      </button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            'mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.12]',
            'text-[13px] font-semibold text-white/90 cursor-pointer transition-all duration-200 hover:bg-white/[0.18]',
          )}
        >
          M
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">{WORKSPACE_LABEL}</TooltipContent>
    </Tooltip>
  );
}

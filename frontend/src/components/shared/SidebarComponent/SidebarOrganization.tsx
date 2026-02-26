'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
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
        className="flex w-full items-center gap-2.5 rounded-md p-2 transition-colors hover:bg-white/15"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/20 text-sm font-semibold text-white">
          M
        </div>
        <span className="flex-1 truncate text-left text-sm font-semibold text-white">
          {WORKSPACE_LABEL}
        </span>
        <ChevronDown size={16} className="shrink-0 text-white/60" />
      </button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            'mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-white/20',
            'text-sm font-semibold text-white cursor-pointer',
          )}
        >
          M
        </button>
      </TooltipTrigger>
      <TooltipContent side="right">{WORKSPACE_LABEL}</TooltipContent>
    </Tooltip>
  );
}

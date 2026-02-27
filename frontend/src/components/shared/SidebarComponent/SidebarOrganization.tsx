'use client';

import { CustomButton } from '@/components/shared';
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
      <CustomButton
        type="text"
        fullWidth
        htmlType="button"
        className="flex items-center gap-2.5 rounded-sm px-2 py-2 text-foreground transition-colors hover:bg-sidebar-accent/50"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-muted text-[13px] font-semibold text-foreground">
          M
        </div>
        <span className="flex-1 truncate text-left text-[13px] font-medium text-foreground">
          {WORKSPACE_LABEL}
        </span>
        <ChevronDown size={14} className="shrink-0 text-muted-foreground" />
      </CustomButton>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <CustomButton
          type="text"
          htmlType="button"
          className={cn(
            'mx-auto flex h-8 w-8 items-center justify-center rounded-sm bg-muted',
            'text-[13px] font-semibold text-foreground transition-colors hover:bg-muted/80',
          )}
        >
          M
        </CustomButton>
      </TooltipTrigger>
      <TooltipContent side="right">{WORKSPACE_LABEL}</TooltipContent>
    </Tooltip>
  );
}

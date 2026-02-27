'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/utils/cn';
import type { SidebarMenuItem } from '@/types/sidebar';
import Link from 'next/link';

export interface SidebarItemMenuProps {
  item: SidebarMenuItem;
  active: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

export function SidebarItemMenu({ item, active, isCollapsed, onClick }: SidebarItemMenuProps) {
  const { icon: Icon, path, title } = item;

  const content = (
    <Link
      href={path}
      onClick={onClick}
      className={cn(
        'flex items-center rounded-sm no-underline transition-colors',
        isCollapsed ? 'mx-auto h-10 w-10 justify-center' : 'gap-3 px-3 py-2',
        active
          ? 'bg-sidebar-accent text-foreground'
          : 'text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground',
      )}
    >
      <Icon className={cn('h-4 w-4 shrink-0', active ? 'text-foreground' : 'text-current')} />
      {!isCollapsed && <span className="text-sm font-medium">{title}</span>}
    </Link>
  );

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right">{title}</TooltipContent>
      </Tooltip>
    );
  }

  return content;
}

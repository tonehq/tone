'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { SidebarMenuItem } from '@/types/sidebar';
import Link from 'next/link';

export interface SidebarItemMenuProps {
  item: SidebarMenuItem;
  active: boolean;
  isCollapsed: boolean;
  onClick?: () => void;
}

const ICON_SIZE = 22;

export function SidebarItemMenu({ item, active, isCollapsed, onClick }: SidebarItemMenuProps) {
  const { icon: Icon, path, title } = item;

  const content = (
    <Link
      href={path}
      onClick={onClick}
      className={cn(
        'flex items-center rounded-md no-underline transition-colors duration-200',
        isCollapsed ? 'mx-auto h-10 w-10 justify-center' : 'gap-2.5 px-3 py-2',
        active ? 'bg-white/90 text-gray-900' : 'text-white/80 hover:bg-white/15 hover:text-white',
      )}
    >
      <Icon size={ICON_SIZE} className={cn(active ? 'text-gray-900' : 'text-current')} />
      {!isCollapsed && (
        <span className={cn('text-sm', active ? 'font-medium text-gray-900' : 'text-current')}>
          {title}
        </span>
      )}
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

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

export function SidebarItemMenu({ item, active, isCollapsed, onClick }: SidebarItemMenuProps) {
  const { icon: Icon, path, title } = item;

  const content = (
    <Link
      href={path}
      onClick={onClick}
      className={cn(
        'group relative flex items-center rounded-lg no-underline transition-all duration-200',
        isCollapsed ? 'mx-auto h-10 w-10 justify-center' : 'gap-2.5 px-2.5 py-2',
        active
          ? 'bg-white/[0.15] text-white shadow-sm shadow-black/10'
          : 'text-white/60 hover:bg-white/[0.08] hover:text-white/90',
      )}
    >
      {active && !isCollapsed && (
        <div className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-white/80" />
      )}
      <Icon
        size={20}
        className={cn(
          'shrink-0 transition-colors duration-200',
          active ? 'text-white' : 'text-current',
        )}
      />
      {!isCollapsed && (
        <span
          className={cn(
            'text-[13px] transition-colors duration-200',
            active ? 'font-medium text-white' : 'text-current',
          )}
        >
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

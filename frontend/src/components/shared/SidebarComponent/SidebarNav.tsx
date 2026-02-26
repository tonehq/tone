'use client';

import { cn } from '@/lib/utils';
import { sidebarSections } from '@/constants/sidebar';
import type { SidebarMenuItem } from '@/types/sidebar';
import { usePathname } from 'next/navigation';
import { SidebarItemMenu } from './SidebarItemMenu';

export interface SidebarNavProps {
  isExpanded: boolean;
  onMenuClick?: () => void;
}

export function SidebarNav({ isExpanded, onMenuClick }: SidebarNavProps) {
  const pathname = usePathname();
  const isActive = (path: string) => pathname === path || pathname?.startsWith(`${path}/`);

  return (
    <div className={cn('flex-1 overflow-y-auto py-4', isExpanded ? 'px-3' : 'px-2')}>
      {sidebarSections.map((section) => (
        <div key={section.heading} className="mb-4">
          {isExpanded && (
            <span className="px-1 text-[11px] font-semibold uppercase tracking-widest text-white/50">
              {section.heading}
            </span>
          )}

          <div className={cn('mt-1.5 flex flex-col gap-1', !isExpanded && 'items-center')}>
            {section.items.map((item: SidebarMenuItem) => (
              <SidebarItemMenu
                key={item.key}
                item={item}
                active={isActive(item.path)}
                isCollapsed={!isExpanded}
                onClick={onMenuClick}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

'use client';

import { cn } from '@/utils/cn';
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
    <div className={cn('flex-1 overflow-y-auto py-3', isExpanded ? 'px-2.5' : 'px-2')}>
      {sidebarSections.map((section) => (
        <div key={section.heading} className="mb-5">
          {isExpanded && (
            <span className="mb-1.5 block px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-white/40">
              {section.heading}
            </span>
          )}

          <div className={cn('flex flex-col gap-0.5', !isExpanded && 'items-center')}>
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

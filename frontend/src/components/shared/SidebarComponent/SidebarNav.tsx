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
    <nav className={cn('flex-1 overflow-y-auto py-3', isExpanded ? 'px-3' : 'px-2')}>
      {sidebarSections.map((section, index) => (
        <div key={section.heading}>
          {isExpanded ? (
            <div className="mb-4">
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {section.heading}
              </p>
              <div className="flex flex-col gap-0.5">
                {section.items.map((item: SidebarMenuItem) => (
                  <SidebarItemMenu
                    key={item.key}
                    item={item}
                    active={isActive(item.path)}
                    isCollapsed={false}
                    onClick={onMenuClick}
                  />
                ))}
              </div>
            </div>
          ) : (
            <>
              {index > 0 && <div className="mx-1 my-1.5 border-t" />}
              <div className="flex flex-col items-center gap-0.5">
                {section.items.map((item: SidebarMenuItem) => (
                  <SidebarItemMenu
                    key={item.key}
                    item={item}
                    active={isActive(item.path)}
                    isCollapsed={true}
                    onClick={onMenuClick}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      ))}
    </nav>
  );
}

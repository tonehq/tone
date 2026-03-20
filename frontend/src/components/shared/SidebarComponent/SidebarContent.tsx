'use client';

import { Divider } from '@/components/shared';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import ProfileMenu from '@/components/shared/userMenu';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';
import { cn } from '@/utils/cn';
import { SidebarHeader } from './SidebarHeader';
import { SidebarNav } from './SidebarNav';
import { SidebarOrganization } from './SidebarOrganization';

export interface SidebarContentProps {
  isExpanded: boolean;
  onToggle: () => void;
  isMobile?: boolean;
  onMenuClick?: () => void;
}

export function SidebarContent({
  isExpanded,
  onToggle,
  isMobile = false,
  onMenuClick,
}: SidebarContentProps) {
  return (
    <div
      className="flex h-full flex-col overflow-hidden bg-sidebar transition-[width] duration-300"
      style={{
        width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
      }}
    >
      <SidebarHeader isExpanded={isExpanded} onToggle={onToggle} isMobile={isMobile} />

      <div className={cn('py-2', isExpanded ? 'px-2.5' : 'flex justify-center px-2')}>
        <SidebarOrganization isExpanded={isExpanded} />
      </div>

      <Divider className="mx-3" />

      <SidebarNav isExpanded={isExpanded} onMenuClick={isMobile ? onMenuClick : undefined} />

      <Divider className="mx-3 mt-auto" />

      {/* Theme toggle */}
      <div className={cn('py-2', isExpanded ? 'px-3' : 'flex justify-center px-2')}>
        {isExpanded ? (
          <ThemeToggle className="h-8 w-full justify-start gap-2 rounded-lg border-0 bg-transparent px-3 text-[13px] font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground" />
        ) : (
          <ThemeToggle className="h-9 w-9 rounded-lg border-0 bg-transparent text-muted-foreground hover:bg-muted/60 hover:text-foreground" />
        )}
      </div>

      <Divider className="mx-3" />

      <div className={cn('py-3', isExpanded ? 'px-2.5' : 'flex justify-center px-2')}>
        <ProfileMenu isExpanded={isExpanded} />
      </div>
    </div>
  );
}

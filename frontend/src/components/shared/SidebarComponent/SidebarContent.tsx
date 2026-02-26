'use client';

import ProfileMenu from '@/components/shared/userMenu';
import { cn } from '@/lib/utils';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';
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
      className={cn(
        'flex h-full flex-col overflow-hidden rounded-md text-white transition-[width] duration-300',
      )}
      style={{
        width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
        background: 'linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%)',
      }}
    >
      <SidebarHeader isExpanded={isExpanded} onToggle={onToggle} isMobile={isMobile} />

      <div className="mx-2 border-t border-white/10" />

      <div className="p-2">
        <SidebarOrganization isExpanded={isExpanded} />
      </div>

      <div className="mx-2 border-t border-white/10" />

      <SidebarNav isExpanded={isExpanded} onMenuClick={isMobile ? onMenuClick : undefined} />

      <div className="mx-2 border-t border-white/10" />

      <div className="p-2">
        <ProfileMenu isExpanded={isExpanded} />
      </div>
    </div>
  );
}

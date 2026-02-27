'use client';

import ProfileMenu from '@/components/shared/userMenu';
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
      className="flex h-full flex-col overflow-hidden text-white transition-[width] duration-300"
      style={{
        width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
        background: 'linear-gradient(180deg, #1a1642 0%, #251f5e 40%, #2d1b69 100%)',
      }}
    >
      <SidebarHeader isExpanded={isExpanded} onToggle={onToggle} isMobile={isMobile} />

      <div className="mx-3 border-t border-white/[0.08]" />

      <div className="px-2.5 py-2.5">
        <SidebarOrganization isExpanded={isExpanded} />
      </div>

      <div className="mx-3 border-t border-white/[0.08]" />

      <SidebarNav isExpanded={isExpanded} onMenuClick={isMobile ? onMenuClick : undefined} />

      <div className="mt-auto mx-3 border-t border-white/[0.08]" />

      <div className="px-2.5 py-3">
        <ProfileMenu isExpanded={isExpanded} />
      </div>
    </div>
  );
}

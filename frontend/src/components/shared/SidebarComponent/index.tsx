'use client';

import { Sheet, SheetContent } from '@/components/ui/sheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { SIDEBAR_WIDTH_COLLAPSED, SIDEBAR_WIDTH_EXPANDED } from '@/constants/sidebar';
import { SidebarContent } from './SidebarContent';

interface SidebarComponentProps {
  isExpanded: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

const SidebarComponent = ({
  isExpanded,
  onToggle,
  mobileOpen,
  onMobileClose,
}: SidebarComponentProps) => {
  const isMobile = useMediaQuery('(max-width: 767px)');

  if (isMobile) {
    return (
      <Sheet open={mobileOpen} onOpenChange={(open) => !open && onMobileClose()}>
        <SheetContent side="left" className="w-[240px] p-0" showCloseButton={false}>
          <SidebarContent
            isExpanded={true}
            onToggle={onToggle}
            isMobile={true}
            onMenuClick={onMobileClose}
          />
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <div
      className="fixed left-0 top-0 h-screen overflow-hidden border-r border-border transition-[width] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
      style={{
        width: isExpanded ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED,
      }}
    >
      <SidebarContent isExpanded={isExpanded} onToggle={onToggle} isMobile={false} />
    </div>
  );
};

export { SidebarComponent as default };

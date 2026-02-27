'use client';

import { CustomButton } from '@/components/shared';
import Logo from '@/components/shared/Logo';
import { cn } from '@/utils/cn';
import { PanelLeft, PanelRight } from 'lucide-react';

export interface SidebarHeaderProps {
  isExpanded: boolean;
  onToggle: () => void;
  isMobile?: boolean;
}

export function SidebarHeader({ isExpanded, onToggle, isMobile = false }: SidebarHeaderProps) {
  return (
    <div
      className={cn(
        'border-b',
        isExpanded
          ? 'flex h-14 items-center justify-between px-5'
          : 'flex flex-col items-center justify-start px-2 py-3',
      )}
    >
      {isExpanded ? (
        <>
          <Logo />
          {!isMobile && (
            <CustomButton
              type="text"
              htmlType="button"
              onClick={onToggle}
              className="h-7 w-7 rounded-sm text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            >
              <PanelLeft size={16} />
            </CustomButton>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <Logo iconOnly />
          <div className="h-px w-6 bg-white/10" />
          {!isMobile && (
            <CustomButton
              type="text"
              htmlType="button"
              onClick={onToggle}
              className="h-7 w-7 rounded-sm text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            >
              <PanelRight className="h-4 w-4" />
            </CustomButton>
          )}
        </div>
      )}
    </div>
  );
}

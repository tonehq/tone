'use client';

import Logo from '@/components/shared/Logo';
import { cn } from '@/lib/utils';
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
        'flex min-h-[60px] items-center px-4 py-3',
        isExpanded ? 'justify-between' : 'justify-center',
      )}
    >
      {isExpanded ? <Logo inverted /> : <Logo inverted iconOnly />}

      {!isMobile && (
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg p-1.5 text-white/50 transition-all duration-200 hover:bg-white/10 hover:text-white/90"
        >
          {isExpanded ? <PanelLeft size={18} /> : <PanelRight size={18} />}
        </button>
      )}
    </div>
  );
}

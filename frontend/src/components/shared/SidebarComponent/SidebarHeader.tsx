'use client';

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
        'flex min-h-14 items-center p-4',
        isExpanded ? 'justify-between' : 'justify-center',
      )}
    >
      {isExpanded && (
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
            T
          </div>
          <span className="text-base font-bold text-white">Tone</span>
        </div>
      )}

      {!isMobile && (
        <button
          type="button"
          onClick={onToggle}
          className="rounded-md p-1.5 text-white/70 transition-colors hover:bg-white/15 hover:text-white"
        >
          {isExpanded ? <PanelLeft size={20} /> : <PanelRight size={20} />}
        </button>
      )}
    </div>
  );
}

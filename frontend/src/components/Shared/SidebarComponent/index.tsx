'use client';

import type React from 'react';

import { Divider, Tooltip } from '@mui/material';
import { ArrowLeftToLine, ArrowRightToLine } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/utils/cn';

import Organization from '../Organization';
import { sidemenu } from './constant';

interface SidebarItemProps {
  icon: React.ElementType;
  href: string;
  active?: boolean;
  title?: string;
  isCollapsed: boolean;
}

function SidebarItemMenu({ icon: Icon, href, active, title, isCollapsed }: SidebarItemProps) {
  const content = (
    <Link
      href={href}
      className={cn(
        'flex items-center w-full py-3 px-4 rounded-md cursor-pointer select-none whitespace-nowrap hover:!bg-white/20 !text-white transition-[background,transform] duration-200 ease-in-out',
        {
          '!bg-white/20 shadow-md': active,
        },
      )}
    >
      <Icon className="w-5 h-5 flex-shrink-0" />
      {!isCollapsed && <span className="ml-3 font-medium">{title}</span>}
    </Link>
  );

  if (isCollapsed) {
    return (
      <Tooltip title={title} placement="right" arrow>
        {content}
      </Tooltip>
    );
  }

  return content;
}

function Sidebar(props: any) {
  const { isSidebarExpanded, setIsSidebarExpanded } = props;
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full bg-[#3f3f46]">
      <div className="flex-1 overflow-y-auto">
        <Organization isSidebarExpanded={isSidebarExpanded} />
        <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.1)', margin: '8px 0' }} />
        <nav className="flex-1 space-y-3">
          {sidemenu.map((item) => {
            const itemPath = (item as any).path || (item as any).href;
            const isActive = pathname === itemPath || pathname?.startsWith(`${itemPath}/`);
            return (
              <SidebarItemMenu
                key={itemPath}
                icon={item.icon}
                href={itemPath}
                active={isActive}
                title={item.title}
                isCollapsed={!isSidebarExpanded}
              />
            );
          })}
        </nav>
      </div>
      <div className="p-4 border-t border-white/10">
        <button
          onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
          className="w-full flex items-center justify-center p-2 rounded-md hover:bg-white/10 text-white transition-colors"
        >
          {isSidebarExpanded ? (
            <ArrowLeftToLine className="w-5 h-5" />
          ) : (
            <ArrowRightToLine className="w-5 h-5" />
          )}
        </button>
      </div>
    </div>
  );
}

export default Sidebar;

'use client';

import type React from 'react';

import { Divider, Tooltip } from '@mui/material';
import { useAtom } from 'jotai';
import { ArrowLeftToLine, ArrowRightToLine } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { authAtom } from '@/atoms/AuthAtom';

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
        'flex items-center rounded-md cursor-pointer select-none whitespace-nowrap transition-all duration-200',
        isCollapsed
          ? 'justify-center w-10 h-10 mx-auto hover:bg-white/20'
          : 'w-full py-3 px-4 hover:bg-white/20',
        active && 'bg-white/20',
      )}
    >
      <Icon className={cn('w-5 h-5 text-white', !isCollapsed && 'mr-3')} />
      {!isCollapsed && <span className="text-sm text-white font-medium">{title}</span>}
    </Link>
  );

  return isCollapsed ? (
    <Tooltip title={title} placement="right" arrow>
      {content}
    </Tooltip>
  ) : (
    content
  );
}

function Sidebar(props: any) {
  const { isSidebarExpanded, setIsSidebarExpanded } = props;
  const pathname = usePathname();
  const [authState] = useAtom(authAtom);

  const isActive = (path: string) =>
    pathname === path || pathname?.split('/')[1] === path.split('/')[1];

  const userName = authState.user
    ? `${authState.user.first_name || ''} ${authState.user.last_name || ''}`.trim() ||
      authState.user.username ||
      authState.user.email
    : 'User';

  return (
    <aside className="flex flex-col h-full bg-[#3f3f46] gap-2">
      {/* Header Section */}
      <div className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className={cn('flex items-center gap-2', !isSidebarExpanded && 'mx-auto')}>
            <div className="flex items-center justify-center w-9 h-9 bg-[#1d4ed8] rounded-md text-white font-semibold text-lg">
              T
            </div>
            {isSidebarExpanded && (
              <span className="text-lg font-semibold text-white">Tone App</span>
            )}
          </div>
          {isSidebarExpanded && (
            <button
              onClick={() => setIsSidebarExpanded(false)}
              className="flex items-center justify-center w-8 h-8 p-1.5 rounded-sm bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              <ArrowLeftToLine className="text-gray-700" size={18} />
            </button>
          )}
        </div>
      </div>

      <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />

      {/* Expand Button (Collapsed Only) */}
      {!isSidebarExpanded && (
        <>
          <div className="flex justify-center gap-2">
            <button
              onClick={() => setIsSidebarExpanded(true)}
              className="flex items-center justify-center w-10 h-10 p-1.5 rounded-sm bg-[#f0f0f0] hover:bg-gray-200 transition-colors"
            >
              <ArrowRightToLine className="text-[#414651]" size={18} />
            </button>
          </div>
          <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />
        </>
      )}

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Organization Section */}
        <div className="mb-2">
          <Organization isSidebarExpanded={isSidebarExpanded} />
        </div>

        <Divider sx={{ borderColor: '#736f6f', margin: '8px 0' }} />

        {/* Navigation Menu */}
        <nav className={cn('flex flex-col', !isSidebarExpanded ? 'items-center gap-2' : 'gap-1')}>
          {sidemenu.map((item: any) => (
            <SidebarItemMenu
              key={item.key}
              icon={item.icon}
              title={item.title}
              href={item.path}
              active={isActive(item.path)}
              isCollapsed={!isSidebarExpanded}
            />
          ))}
        </nav>
      </div>
    </aside>
  );
}

export default Sidebar;

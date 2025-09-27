'use client';

import type React from 'react';

import { Divider, Tooltip } from 'antd';
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
        'flex items-center w-full py-3 px-4 my-1 mx-4 rounded-md cursor-pointer select-none whitespace-nowrap hover:!bg-white/20 !text-white transition-[background,transform] duration-200 ease-in-out',
        {
          '!bg-white/20 shadow-md': active,
        },
      )}
    >
      <div className="flex items-center justify-center gap-2">
        <Icon className="w-5 h-5" />
        {!isCollapsed && <span className="text-sm">{title}</span>}
      </div>
    </Link>
  );

  return isCollapsed ? (
    <Tooltip placement="right" title={title} mouseEnterDelay={0.05}>
      {content}
    </Tooltip>
  ) : (
    content
  );
}

function Sidebar(props: any) {
  const { isSidebarExpanded, setIsSidebarExpanded } = props;
  const pathname = usePathname();

  const isActive = (path: string) =>
    pathname === path || pathname?.split('/')[1] === path.split('/')[1];

  return (
    <aside className={'h-full !space-y-5 transition-all duration-1000 ease-in-out'}>
      <div className="flex items-center justify-between w-full">
        <div className={cn('flex items-center gap-2', !isSidebarExpanded && 'm-auto')}>
          <div
            className={'flex items-center size-9 justify-center text-white bg-blue-700 rounded-md'}
          >
            <span className="text-md font-semibold">T</span>
          </div>
          {isSidebarExpanded && <div className="text-lg font-semibold py-2">Tone App</div>}
        </div>
        {isSidebarExpanded && (
          <button
            onClick={() => setIsSidebarExpanded(false)}
            className="p-2 rounded-md bg-gray-100 my-shadow cursor-pointer"
          >
            <ArrowLeftToLine className="text-gray-700" size={20} />
          </button>
        )}
      </div>
      <Divider className="bg-[#736f6f]" style={{ marginBlock: 12 }} />
      {!isSidebarExpanded && (
        <>
          <div
            className={
              'cursor-pointer bg-[#f0f0f0] p-2 my-shadow flex justify-center rounded-md opacity-100'
            }
            onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
          >
            <ArrowRightToLine color="#414651" size={20} />
          </div>
          <Divider className="bg-[#736f6f]" style={{ marginBlock: 12 }} />
        </>
      )}

      <Organization isSidebarExpanded={isSidebarExpanded} />
      <Divider className="bg-[#736f6f]" style={{ marginBlock: 12 }} />

      <nav className="flex flex-col items-center gap-1.5 rounded-md">
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
    </aside>
  );
}

export default Sidebar;

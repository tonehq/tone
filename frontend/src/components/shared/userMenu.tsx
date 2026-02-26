'use client';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useAtom, useSetAtom } from 'jotai';
import { startCase } from 'lodash';
import { ChevronDown, LogOut, User } from 'lucide-react';
import { useEffect } from 'react';

interface ProfileMenuProps {
  isExpanded: boolean;
}

function UserAvatar({ initial }: { initial: string }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-400 text-xs font-semibold text-white">
      {initial}
    </div>
  );
}

export default function ProfileMenu({ isExpanded }: ProfileMenuProps) {
  const [authState] = useAtom(authAtom);
  const getCurrentUser = useSetAtom(getCurrentUserAtom);
  const logout = useSetAtom(logoutAtom);

  useEffect(() => {
    if (!authState.user && !authState.isLoading) {
      getCurrentUser();
    }
  }, [authState.user, authState.isLoading, getCurrentUser]);

  const userEmail = authState?.user?.email;

  const initial = authState?.user?.first_name
    ? startCase(authState.user.first_name.charAt(0))
    : authState?.user?.email
      ? authState.user.email.charAt(0).toUpperCase()
      : '';

  const trigger = isExpanded ? (
    <div className="mt-2 flex w-full items-center gap-2 px-2">
      <UserAvatar initial={initial} />
      <span className="max-w-[140px] truncate text-[15px] text-white">{userEmail}</span>
      <ChevronDown size={14} className="shrink-0 text-white/60" />
    </div>
  ) : (
    <div className="mt-2 flex items-center px-2">
      <UserAvatar initial={initial} />
    </div>
  );

  const menu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex cursor-pointer items-center rounded-md px-1.5 py-1.5 transition-colors select-none',
            'hover:bg-white/10',
          )}
        >
          {trigger}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="right" align="end" className="w-52">
        <DropdownMenuItem>
          <User className="size-4" />
          View Profile
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onClick={() => logout()}>
          <LogOut className="size-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (!isExpanded) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div>{menu}</div>
        </TooltipTrigger>
        <TooltipContent side="right">{userEmail || 'Profile'}</TooltipContent>
      </Tooltip>
    );
  }

  return menu;
}

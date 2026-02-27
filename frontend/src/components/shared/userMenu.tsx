'use client';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';
import { CustomButton } from '@/components/shared';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/utils/cn';
import { useAtom, useSetAtom } from 'jotai';
import { startCase } from 'lodash';
import { ChevronDown, LogOut, User } from 'lucide-react';
import { useEffect } from 'react';

interface ProfileMenuProps {
  isExpanded: boolean;
}

function UserAvatar({ initial }: { initial: string }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-400/90 text-xs font-bold text-white">
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
    <div className="flex w-full items-center gap-2.5">
      <UserAvatar initial={initial} />
      <span className="max-w-[120px] truncate text-[13px] text-muted-foreground">{userEmail}</span>
      <ChevronDown size={14} className="ml-auto shrink-0 text-muted-foreground" />
    </div>
  ) : (
    <UserAvatar initial={initial} />
  );

  const menu = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <CustomButton
          type="text"
          htmlType="button"
          className={cn(
            'flex w-full items-center rounded-sm px-2 py-2 transition-colors select-none',
            'hover:bg-sidebar-accent/50',
          )}
        >
          {trigger}
        </CustomButton>
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

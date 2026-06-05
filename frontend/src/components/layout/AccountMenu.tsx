'use client';

import { ChevronDown, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { AvatarBadge } from '@/components/layout/AvatarBadge';
import { ThemeToggleRow } from '@/components/layout/ThemeToggleRow';
import { CustomButton } from '@/components/shared';
import { Popover, PopoverContent, PopoverTrigger, Separator } from '@/components/ui/primitives';
import { getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

// Shared account menu used by BOTH the main app sidebar and the settings rail.
// The two only differ in the extra links shown above the theme toggle (the app
// sidebar adds a "Settings" entry), so consumers pass those via `children`.
export function AccountMenu({
  collapsed,
  children,
}: {
  collapsed: boolean;
  children?: React.ReactNode;
}) {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    router.replace('/login');
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        {collapsed ? (
          <CustomButton
            type="text"
            aria-label="Account menu"
            className="mx-auto size-10 rounded-lg p-0 hover:bg-sidebar-accent/60"
          >
            <AvatarBadge size="md">{getInitials(user?.first_name, user?.last_name)}</AvatarBadge>
          </CustomButton>
        ) : (
          <CustomButton
            type="text"
            fullWidth
            className="h-auto justify-start gap-2.5 rounded-lg px-2 py-1.5 text-left font-normal hover:bg-sidebar-accent/60"
          >
            <AvatarBadge size="sm">{getInitials(user?.first_name, user?.last_name)}</AvatarBadge>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-medium leading-tight">
                {user?.first_name || user?.email || 'Account'}
              </span>
            </span>
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          </CustomButton>
        )}
      </PopoverTrigger>
      <PopoverContent
        side={collapsed ? 'right' : 'top'}
        align="start"
        sideOffset={10}
        className="w-60 p-0"
      >
        <div className="px-4 py-3">
          <p className="text-sm font-semibold">
            {user?.first_name} {user?.last_name}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <Separator />
        <div className="space-y-0.5 p-1.5">
          {children}
          <ThemeToggleRow />
        </div>
        <Separator />
        <div className="p-1.5">
          <CustomButton
            type="text"
            fullWidth
            onClick={handleLogout}
            icon={<LogOut className="h-4 w-4" />}
            className="h-9 justify-start gap-3 px-3 font-normal text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            Log out
          </CustomButton>
        </div>
      </PopoverContent>
    </Popover>
  );
}

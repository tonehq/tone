'use client';

import { ChevronDown, LogOut, Settings } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { AvatarBadge } from '@/components/layout/AvatarBadge';
import { ThemeToggleRow } from '@/components/layout/ThemeToggleRow';
import { CustomButton } from '@/components/shared';
import { Popover, PopoverContent, PopoverTrigger, Separator } from '@/components/ui/primitives';
import { authApi } from '@/lib/api/auth';
import { getInitials } from '@/lib/utils';
import { useAuthStore, REFRESH_TOKEN } from '@/stores/auth';

/** Standard "Settings" entry for the account menu. Every rail except the
 * settings rail itself (where you're already in Settings) passes this as
 * `children` so the shortcut stays consistent across the app sidebar, the
 * agent editor rail, and the call-detail rail. */
export function AccountMenuSettingsLink() {
  return (
    <Link
      href="/settings"
      className="flex h-9 w-full items-center gap-3 rounded-md px-3 text-sm font-normal text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
    >
      <Settings className="h-4 w-4 text-muted-foreground" />
      Settings
    </Link>
  );
}

// Shared account menu used by the main app sidebar, the agent editor rail,
// the call-detail rail, and the settings rail. They only differ in the extra
// links shown above the theme toggle (most add `AccountMenuSettingsLink`; the
// settings rail adds none), so consumers pass those via `children`.
export function AccountMenu({
  collapsed,
  children,
}: {
  collapsed: boolean;
  children?: React.ReactNode;
}) {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = async () => {
    // Capture the refresh token BEFORE wiping storage so we can hand it
    // to the backend, which uses it to revoke the matching session row.
    const refreshToken = typeof window !== 'undefined' ? localStorage.getItem(REFRESH_TOKEN) : null;
    try {
      if (refreshToken) {
        await authApi.logout({ refresh_token: refreshToken });
      }
    } catch (error) {
      // Logout is best-effort on the server; we still log the user out locally.
      console.error('Logout error:', error);
    } finally {
      clearAuth();
      router.replace('/login');
    }
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

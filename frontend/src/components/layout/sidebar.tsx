'use client';

import {
  BookOpen,
  Bot,
  Boxes,
  Building2,
  Check,
  ChevronsUpDown,
  Home,
  Phone,
  Settings,
  Workflow,
  Wrench,
} from 'lucide-react';
import Link from 'next/link';

import { AccountMenu } from '@/components/layout/AccountMenu';
import { SidebarShell, type SidebarNavGroup } from '@/components/layout/SidebarShell';
import { CustomButton } from '@/components/shared';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
  Separator,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/primitives';
import { useNavigation } from '@/contexts/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

const NAV_SECTIONS: SidebarNavGroup[] = [
  {
    heading: 'General',
    items: [{ label: 'Home', href: '/home', icon: Home }],
  },
  {
    heading: 'Build',
    items: [
      { label: 'Agents', href: '/agents', icon: Bot },
      { label: 'Workflows', href: '/workflows', icon: Workflow },
      { label: 'Tools', href: '/tools', icon: Wrench },
      { label: 'MCP', href: '/mcp', icon: Boxes },
      { label: 'Knowledge Base', href: '/knowledge-base', icon: BookOpen },
      { label: 'Call History', href: '/call-history', icon: Phone },
    ],
  },
];

function formatRole(role: string | null | undefined): string {
  if (!role) return 'member';
  return role.toString().toLowerCase().replace(/_/g, ' ');
}

/** Primary slot — workspace identity + organization switcher. */
function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const { user, organization, organizations, activeOrgId, setActiveOrgId } = useAuthStore();

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 ring-1 ring-primary/10">
            <Building2 className="h-4 w-4 text-primary/70" />
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={12}>
          {organization?.name || 'Workspace'}
        </TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <CustomButton
          type="text"
          fullWidth
          aria-label="Switch organization"
          className="h-auto justify-start gap-3 rounded-lg px-2 py-2 text-left font-normal hover:bg-sidebar-accent/60"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/10">
            <Building2 className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[14px] font-semibold leading-tight tracking-tight">
              {organization?.name || 'My Workspace'}
            </p>
            <p className="mt-0.5 truncate text-[11.5px] leading-tight text-muted-foreground">
              {formatRole(user?.role)}
            </p>
          </div>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
        </CustomButton>
      </PopoverTrigger>
      <PopoverContent align="start" side="bottom" sideOffset={6} className="w-[248px] p-0">
        <div className="border-b border-border/60 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
            Workspace
          </p>
          <p className="mt-1 truncate text-[12.5px] text-muted-foreground">{user?.email ?? '—'}</p>
        </div>
        {organizations.length > 0 ? (
          <div className="max-h-64 overflow-y-auto p-1.5">
            {organizations.map((org) => {
              const isActive = String(org.id) === String(activeOrgId ?? organization?.id);
              return (
                <CustomButton
                  key={org.id}
                  type="text"
                  onClick={() => {
                    if (String(org.id) === String(activeOrgId ?? organization?.id)) {
                      return;
                    }
                    setActiveOrgId(String(org.id));
                    // Reload so the new tenant_id header is picked up
                    // by every in-flight & queued request.
                    if (typeof window !== 'undefined') {
                      window.location.reload();
                    }
                  }}
                  className={cn(
                    'h-auto w-full justify-start gap-2.5 rounded-md px-2 py-1.5 text-left text-[13px] font-normal',
                    isActive
                      ? 'cursor-default bg-sidebar-accent text-foreground hover:bg-sidebar-accent'
                      : 'text-foreground/85 hover:bg-sidebar-accent/60',
                  )}
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[11px] font-semibold text-primary">
                    {(org.name ?? 'W').charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{org.name}</p>
                    {org.role && (
                      <p className="truncate text-[11px] text-muted-foreground">
                        {formatRole(org.role)}
                      </p>
                    )}
                  </div>
                  {isActive && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
                </CustomButton>
              );
            })}
          </div>
        ) : (
          <div className="px-3 py-2.5 text-[12px] text-muted-foreground">
            You belong to one workspace.
          </div>
        )}
        <Separator />
        <div className="p-1.5">
          <Link
            href="/settings/organizations"
            className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-foreground/85 hover:bg-sidebar-accent/60"
          >
            <Settings className="h-3.5 w-3.5 text-muted-foreground" />
            Manage organizations
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/** Footer slot — account menu with a Settings shortcut. */
function AppUserMenu({ collapsed }: { collapsed: boolean }) {
  return (
    <AccountMenu collapsed={collapsed}>
      <Link
        href="/settings"
        className="flex h-9 w-full items-center gap-3 rounded-md px-3 text-sm font-normal text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <Settings className="h-4 w-4 text-muted-foreground" />
        Settings
      </Link>
    </AccountMenu>
  );
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  return (
    <SidebarShell
      groups={NAV_SECTIONS}
      collapsed={sidebarCollapsed}
      onToggle={toggleSidebar}
      activeLayoutId="app-sidebar"
      className="fixed bottom-0 left-0 top-0 z-40"
      primary={(collapsed) => <WorkspaceSwitcher collapsed={collapsed} />}
      footer={(collapsed) => <AppUserMenu collapsed={collapsed} />}
    />
  );
}

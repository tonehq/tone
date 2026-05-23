'use client';

import { AnimatePresence, motion } from 'framer-motion';
import {
  BookOpen,
  Bot,
  Boxes,
  Building2,
  Cable,
  Check,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  ChevronsUpDown,
  Home,
  LogOut,
  Moon,
  Phone,
  Plug,
  Settings,
  Sun,
  Users,
  Wrench,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

import { Logo, LogoIcon } from '@/components/ui/logo';
import { Button } from '@/components/ui/button';
import { Separator, Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/primitives';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/primitives';

function AvatarBadge({ children, size = 'md' }: { children: React.ReactNode; size?: 'sm' | 'md' }) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary',
        size === 'md' ? 'h-8 w-8' : 'h-7 w-7',
      )}
    >
      {children}
    </div>
  );
}
import { useNavigation } from '@/contexts/navigation';
import { useAuthStore } from '@/stores/auth';
import { cn, getInitials } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavSection {
  heading: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    heading: 'General',
    items: [{ label: 'Home', href: '/home', icon: Home }],
  },
  {
    heading: 'Build',
    items: [
      { label: 'Agents', href: '/agents', icon: Bot },
      { label: 'Tools', href: '/tools', icon: Wrench },
      { label: 'MCP', href: '/mcp', icon: Boxes },
      { label: 'Knowledge Base', href: '/knowledge-base', icon: BookOpen },
      { label: 'Call History', href: '/call-history', icon: Phone },
    ],
  },
  {
    heading: 'Settings',
    items: [
      { label: 'Model Providers', href: '/model-providers', icon: Plug },
      { label: 'Integrations', href: '/integrations', icon: Cable },
      { label: 'Phone Numbers', href: '/phone-numbers', icon: Phone },
      { label: 'Organizations', href: '/organizations', icon: Building2 },
      { label: 'Members', href: '/members', icon: Users },
    ],
  },
];

function NavLink({
  href,
  icon: Icon,
  label,
  active,
  collapsed,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active: boolean;
  collapsed: boolean;
}) {
  const content = (
    <Link
      href={href}
      className={cn(
        'group relative flex items-center rounded-md text-[13px] font-medium transition-all duration-150',
        active
          ? 'bg-sidebar-accent text-foreground'
          : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
        collapsed ? 'justify-center w-10 h-10 mx-auto' : 'gap-2.5 px-2.5 py-[7px]',
      )}
    >
      <Icon
        className={cn(
          'shrink-0 transition-colors',
          collapsed ? 'h-[18px] w-[18px]' : 'h-4 w-4',
          active ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground',
        )}
      />
      {!collapsed && <span className="truncate">{label}</span>}
      {active && !collapsed && (
        <motion.div
          layoutId="sidebar-active"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
      {active && collapsed && (
        <motion.div
          layoutId="sidebar-active-collapsed"
          className="absolute -left-[5px] top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={12}>
          {label}
        </TooltipContent>
      </Tooltip>
    );
  }
  return content;
}

function ThemeToggleRow() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = mounted && resolvedTheme === 'dark';
  return (
    <Button
      variant="ghost"
      size="sm"
      fullWidth
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="justify-start gap-3 px-3 h-9 font-normal"
    >
      {isDark ? (
        <>
          <Sun className="h-4 w-4 text-muted-foreground" />
          Light mode
        </>
      ) : (
        <>
          <Moon className="h-4 w-4 text-muted-foreground" />
          Dark mode
        </>
      )}
    </Button>
  );
}

function formatRole(role: string | null | undefined): string {
  if (!role) return 'member';
  return role.toString().toLowerCase().replace(/_/g, ' ');
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { sidebarCollapsed, toggleSidebar } = useNavigation();
  const { user, organization, organizations, activeOrgId, setActiveOrgId, clearAuth } =
    useAuthStore();

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const handleLogout = () => {
    clearAuth();
    router.replace('/login');
  };

  const collapsed = sidebarCollapsed;

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 60 : 240 }}
      transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
      className="fixed top-0 bottom-0 left-0 z-40 flex flex-col border-r border-sidebar-border bg-sidebar"
    >
      <div className="shrink-0 border-b border-sidebar-border">
        {collapsed ? (
          <div className="flex flex-col items-center py-3 gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Link href="/home" className="block">
                  <LogoIcon className="h-8 w-8" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={12}>
                Tone
              </TooltipContent>
            </Tooltip>
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
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between h-12 px-4">
              <Link href="/home">
                <Logo size="sm" />
              </Link>
              <button
                onClick={toggleSidebar}
                className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-foreground/[0.06] hover:text-foreground transition-colors cursor-pointer"
                aria-label="Collapse sidebar"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
            </div>
            <div className="px-3 pb-3 pt-1">
              <Popover>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-sidebar-accent/60 cursor-pointer"
                    aria-label="Switch organization"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/10">
                      <Building2 className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-[14px] font-semibold leading-tight tracking-tight">
                        {organization?.name || 'My Workspace'}
                      </p>
                      <p className="mt-0.5 truncate text-[11.5px] leading-tight text-muted-foreground">
                        {formatRole(user?.role)}
                      </p>
                    </div>
                    <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  align="start"
                  side="bottom"
                  sideOffset={6}
                  className="w-[248px] p-0"
                >
                  <div className="border-b border-border/60 px-3 py-2.5">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
                      Workspace
                    </p>
                    <p className="mt-1 truncate text-[12.5px] text-muted-foreground">
                      {user?.email ?? '—'}
                    </p>
                  </div>
                  {organizations.length > 0 ? (
                    <div className="max-h-64 overflow-y-auto p-1.5">
                      {organizations.map((org) => {
                        const isActive = String(org.id) === String(activeOrgId ?? organization?.id);
                        return (
                          <button
                            key={org.id}
                            type="button"
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
                              'flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-[13px] transition-colors',
                              isActive
                                ? 'bg-sidebar-accent text-foreground'
                                : 'text-foreground/85 hover:bg-sidebar-accent/60',
                            )}
                          >
                            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[11px] font-semibold text-primary">
                              {(org.name ?? 'W').charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="truncate font-medium">{org.name}</p>
                              {org.role && (
                                <p className="truncate text-[11px] text-muted-foreground">
                                  {formatRole(org.role)}
                                </p>
                              )}
                            </div>
                            {isActive && <Check className="h-3.5 w-3.5 shrink-0 text-primary" />}
                          </button>
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
                      href="/organizations"
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-foreground/85 hover:bg-sidebar-accent/60"
                    >
                      <Settings className="h-3.5 w-3.5 text-muted-foreground" />
                      Manage organizations
                    </Link>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </>
        )}
      </div>

      {collapsed && (
        <div className="flex justify-center pt-2 pb-1 shrink-0">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={toggleSidebar}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-foreground/[0.06] hover:text-foreground transition-colors cursor-pointer"
                aria-label="Expand sidebar"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={12}>
              Expand sidebar
            </TooltipContent>
          </Tooltip>
        </div>
      )}

      <nav className={cn('flex-1 overflow-y-auto', collapsed ? 'px-[10px] py-1' : 'px-3 py-2')}>
        {NAV_SECTIONS.map((section, sIdx) => (
          <div key={section.heading} className={cn(sIdx > 0 && 'mt-4')}>
            {collapsed ? (
              <AnimatePresence>
                {sIdx > 0 && (
                  <div className="w-6 mx-auto my-1.5 border-t border-sidebar-border/60" />
                )}
              </AnimatePresence>
            ) : (
              <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                {section.heading}
              </p>
            )}
            <div className={cn('space-y-1', collapsed && 'flex flex-col items-center')}>
              {section.items.map((item) => (
                <NavLink
                  key={item.href}
                  href={item.href}
                  icon={item.icon}
                  label={item.label}
                  active={isActive(item.href)}
                  collapsed={collapsed}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div
        className={cn(
          'border-t border-sidebar-border shrink-0',
          collapsed ? 'px-[10px] py-2' : 'px-3 py-2',
        )}
      >
        <Popover>
          <PopoverTrigger asChild>
            {collapsed ? (
              <button className="flex h-10 w-10 mx-auto items-center justify-center rounded-lg hover:bg-sidebar-accent/60 cursor-pointer">
                <AvatarBadge size="md">
                  {getInitials(user?.first_name, user?.last_name)}
                </AvatarBadge>
              </button>
            ) : (
              <button className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-sidebar-accent/60 cursor-pointer transition-colors">
                <AvatarBadge size="sm">
                  {getInitials(user?.first_name, user?.last_name)}
                </AvatarBadge>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium truncate leading-tight">
                    {user?.first_name || user?.email || 'Account'}
                  </p>
                </div>
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              </button>
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
              <p className="text-xs text-muted-foreground truncate mt-0.5">{user?.email}</p>
            </div>
            <Separator />
            <div className="p-1.5 space-y-0.5">
              <Button
                variant="ghost"
                size="sm"
                asChild
                fullWidth
                className="justify-start gap-3 px-3 h-9 font-normal"
              >
                <Link href="/members">
                  <Settings className="h-4 w-4 text-muted-foreground" />
                  Settings
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                asChild
                fullWidth
                className="justify-start gap-3 px-3 h-9 font-normal"
              >
                <Link href="/members">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  Team Members
                </Link>
              </Button>
              <ThemeToggleRow />
            </div>
            <Separator />
            <div className="p-1.5">
              <Button
                variant="ghost"
                size="sm"
                fullWidth
                onClick={handleLogout}
                className="justify-start gap-3 px-3 h-9 font-normal text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </motion.aside>
  );
}

import { Building2, Cable, LayoutGrid, Plug, UserCircle, Users } from 'lucide-react';

// Single source of truth for the settings destinations. Both the settings rail
// (settings/layout.tsx) and the overview landing page (SettingsOverview.tsx)
// derive their navigation from this list so the two can never drift.

export interface SettingsNavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  exact?: boolean;
  // Longer copy shown only on the overview landing page.
  description?: string;
}

export interface SettingsNavGroup {
  // `null` heading = ungrouped (the Overview entry). Such groups are skipped by
  // the overview page, which lists only the labelled sections.
  heading: string | null;
  // Sub-heading shown only on the overview landing page.
  caption?: string;
  items: SettingsNavItem[];
}

export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    heading: null,
    items: [{ label: 'Overview', href: '/settings', icon: LayoutGrid, exact: true }],
  },
  {
    heading: 'Account',
    caption: 'How you show up across the workspace',
    items: [
      {
        label: 'User settings',
        href: '/settings/profile',
        icon: UserCircle,
        description: 'Manage your profile, avatar, and personal account details.',
      },
    ],
  },
  {
    heading: 'Workspace',
    caption: 'Organizations and the people in them',
    items: [
      {
        label: 'Organizations',
        href: '/settings/organizations',
        icon: Building2,
        description: 'Create and switch between the workspaces you belong to.',
      },
      {
        label: 'Members',
        href: '/settings/members',
        icon: Users,
        description: 'Invite teammates and manage their roles and access.',
      },
    ],
  },
  {
    heading: 'Configuration',
    caption: 'Providers and connected services',
    items: [
      {
        label: 'Model Providers',
        href: '/settings/model-providers',
        icon: Plug,
        description: 'Configure LLM, speech-to-text, and text-to-speech provider keys.',
      },
      {
        label: 'Integrations',
        href: '/settings/integrations',
        icon: Cable,
        description: 'Connect external apps and manage API credentials.',
      },
    ],
  },
];

// Flat list of every settings destination — used by the mobile nav.
export const SETTINGS_NAV_ITEMS = SETTINGS_NAV_GROUPS.flatMap((g) => g.items);

export function isSettingsItemActive(pathname: string, item: SettingsNavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

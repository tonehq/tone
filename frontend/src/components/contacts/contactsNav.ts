import { History, Table2, Users } from 'lucide-react';

import type { SidebarNavGroup, SidebarNavItem } from '@/components/layout/SidebarShell';

// Single source of truth for the Contacts focused-section rail. Both the
// contacts rail (contacts/layout.tsx desktop) and its mobile top bar derive
// their navigation from this list so the two can never drift. Mirrors the
// settings navConfig.ts shape.
//
// Distinct leading segments (`directories` vs `datasource`) mean
// `isSidebarItemActive` highlights each item without collision — no `exact`
// needed. `General` stays active across `/contacts/directories` and
// `/contacts/directories/[id]`.

export const CONTACTS_NAV_GROUPS: SidebarNavGroup[] = [
  {
    heading: null,
    items: [
      { label: 'General', href: '/contacts/directories', icon: Users },
      { label: 'Datasource', href: '/contacts/datasource', icon: Table2 },
      { label: 'Sync History', href: '/contacts/sync-history', icon: History },
    ],
  },
];

// Flat list of every contacts destination — used by the mobile nav.
export const CONTACTS_NAV_ITEMS: SidebarNavItem[] = CONTACTS_NAV_GROUPS.flatMap((g) => g.items);

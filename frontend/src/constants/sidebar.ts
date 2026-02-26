import type { SidebarMenuItem, SidebarSection } from '@/types/sidebar';
import { Bot, Home, Phone, Plug } from 'lucide-react';

export const SIDEBAR_WIDTH_EXPANDED = 240;
export const SIDEBAR_WIDTH_COLLAPSED = 72;

export const SIDEBAR_BG = 'linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%)';
export const SIDEBAR_HOVER_ACTIVE = '#e5e7eb';
export const SECTION_HEADING_COLOR = '#6b7280';

export const sidebarSections: SidebarSection[] = [
  {
    heading: 'GENERAL',
    items: [{ key: 'home', title: 'Home', path: '/home', icon: Home }],
  },
  {
    heading: 'BUILD',
    items: [
      { key: 'agents', title: 'Agent', path: '/agents', icon: Bot },
      { key: 'phone-numbers', title: 'Phone Numbers', path: '/phone-numbers', icon: Phone },
    ],
  },
  {
    heading: 'SETTINGS',
    items: [{ key: 'integrations', title: 'Integrations', path: '/settings', icon: Plug }],
  },
];

export const sidemenu: SidebarMenuItem[] = sidebarSections.flatMap(
  (sidebarSection: SidebarSection): SidebarMenuItem[] => sidebarSection.items,
) as SidebarMenuItem[];

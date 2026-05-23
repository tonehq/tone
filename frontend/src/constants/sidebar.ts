import type { SidebarMenuItem, SidebarSection } from '@/types/sidebar';
import {
  BookOpen,
  Bot,
  Boxes,
  Building2,
  Cable,
  Home,
  Phone,
  Plug,
  Users,
  Wrench,
} from 'lucide-react';

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
      { key: 'tools', title: 'Tools', path: '/tools', icon: Wrench },
      { key: 'mcp', title: 'MCP', path: '/mcp', icon: Boxes },
      {
        key: 'knowledge-base',
        title: 'Knowledge Base',
        path: '/knowledge-base',
        icon: BookOpen,
      },
      { key: 'call-history', title: 'Call History', path: '/call-history', icon: Phone },
    ],
  },
  {
    heading: 'SETTINGS',
    items: [
      {
        key: 'model-providers',
        title: 'Model Providers',
        path: '/model-providers',
        icon: Plug,
      },
      { key: 'integrations', title: 'Integrations', path: '/integrations', icon: Cable },
      { key: 'organizations', title: 'Organizations', path: '/organizations', icon: Building2 },
      { key: 'members', title: 'Members', path: '/members', icon: Users },
    ],
  },
];

export const sidemenu: SidebarMenuItem[] = sidebarSections.flatMap(
  (sidebarSection: SidebarSection): SidebarMenuItem[] => sidebarSection.items,
) as SidebarMenuItem[];

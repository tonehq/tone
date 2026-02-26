import type { LucideIcon } from 'lucide-react';

export interface SidebarMenuItem {
  key: string;
  title: string;
  path: string;
  icon: LucideIcon;
}

export interface SidebarSection {
  heading: string;
  items: SidebarMenuItem[];
}

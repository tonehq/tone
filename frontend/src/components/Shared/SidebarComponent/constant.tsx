import { Bot, Cog, LayoutDashboard } from 'lucide-react';

export const sidemenu_ee = [
  {
    key: 1,
    title: 'Home',
    path: '/home',
    icon: LayoutDashboard,
  },
  {
    key: 2,
    title: 'Settings',
    path: '/settings',
    icon: Cog,
  },
  {
    key: 3,
    title: 'Agents',
    path: '/agents',
    icon: Bot, // Or directly import Users above and use icon: Users,
  },
];

export const sidemenu_ce = [
  {
    key: 1,
    title: 'Home',
    path: '/home',
    icon: LayoutDashboard,
  },
  {
    key: 3,
    title: 'Agents',
    path: '/agents',
    icon: Bot, // Or directly import Users above and use icon: Users,
  },
];

import { Bot, Cog, LayoutDashboard } from 'lucide-react';

export const sidemenu = [
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

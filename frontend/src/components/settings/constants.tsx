import { Building, Key, Network, User } from 'lucide-react';

export const settingsSidebar = [
  {
    key: 1,
    title: 'API Key',
    path: '/settings/api-key',
    icon: Key,
  },
  {
    key: 2,
    title: 'Members',
    path: '/settings/members',
    icon: User,
  },
  {
    key: 3,
    title: 'Organization',
    path: '/settings/organization',
    icon: Building,
  },
  {
    key: 4,
    title: 'Web Hook',
    path: '/settings/web-hook',
    icon: Network,
  },
];

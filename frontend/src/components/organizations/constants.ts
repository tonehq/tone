import { Crown, Shield, User } from 'lucide-react';

export interface OrgRow {
  id: string;
  name: string;
  slug: string;
  role: string;
  joined_at: number;
}

export const roleConfig: Record<
  string,
  { icon: typeof Crown; color: string; bg: string; label: string }
> = {
  owner: {
    icon: Crown,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-500/10',
    label: 'Owner',
  },
  admin: {
    icon: Shield,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-500/10',
    label: 'Admin',
  },
  member: {
    icon: User,
    color: 'text-muted-foreground',
    bg: 'bg-muted',
    label: 'Member',
  },
};

const avatarGradients = [
  'from-violet-500 to-purple-600',
  'from-blue-500 to-cyan-500',
  'from-emerald-500 to-teal-500',
  'from-rose-500 to-pink-500',
  'from-amber-500 to-orange-500',
  'from-indigo-500 to-blue-500',
];

export function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

export function getAvatarGradient(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarGradients[Math.abs(hash) % avatarGradients.length];
}

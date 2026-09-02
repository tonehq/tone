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
    color: 'text-primary',
    bg: 'bg-primary/10',
    label: 'Admin',
  },
  member: {
    icon: User,
    color: 'text-muted-foreground',
    bg: 'bg-muted',
    label: 'Member',
  },
};

const avatarTones = [
  'bg-primary/10 text-primary ring-primary/20',
  'bg-sky-500/10 text-sky-700 ring-sky-500/20 dark:text-sky-300 dark:ring-sky-400/25',
  'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300 dark:ring-emerald-400/25',
  'bg-rose-500/10 text-rose-700 ring-rose-500/20 dark:text-rose-300 dark:ring-rose-400/25',
  'bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300 dark:ring-amber-400/25',
  'bg-teal-500/10 text-teal-700 ring-teal-500/20 dark:text-teal-300 dark:ring-teal-400/25',
];

export function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

export function getAvatarTone(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarTones[Math.abs(hash) % avatarTones.length];
}

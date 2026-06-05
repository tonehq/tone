'use client';

import { BadgeCheck, Crown, Mail, ShieldCheck, UserCircle } from 'lucide-react';
import { useState } from 'react';

import { getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/utils/cn';

import ProfileForm from './ProfileForm';

interface AvatarPreviewProps {
  url?: string | null;
  initials: string;
  size?: 'sm' | 'lg';
}

export function AvatarPreview({ url, initials, size = 'lg' }: AvatarPreviewProps) {
  const [broken, setBroken] = useState(false);
  const ringClass =
    size === 'lg'
      ? 'size-20 sm:size-[88px] ring-4 ring-background shadow-[0_8px_28px_-12px_rgba(99,102,241,0.45)]'
      : 'size-10 ring-2 ring-background shadow-sm';
  const labelClass = size === 'lg' ? 'text-2xl tracking-tight' : 'text-[13px]';

  const showImage = url && !broken;

  return (
    <div className="relative shrink-0">
      <div
        className={cn(
          'relative flex items-center justify-center overflow-hidden rounded-full',
          ringClass,
        )}
      >
        {/* Gradient background sits behind the image so transparent PNGs still look intentional */}
        <span
          aria-hidden
          className="absolute inset-0 bg-gradient-to-br from-violet-500 via-indigo-500 to-fuchsia-500"
        />
        {showImage ? (
          <img
            src={url}
            alt="Avatar preview"
            className="relative size-full object-cover"
            onError={() => setBroken(true)}
          />
        ) : (
          <span className={cn('relative font-semibold text-white', labelClass)}>{initials}</span>
        )}
      </div>
      {size === 'lg' && (
        <span
          aria-hidden
          className="absolute -bottom-0.5 -right-0.5 flex size-6 items-center justify-center rounded-full border-2 border-background bg-emerald-500 shadow-sm"
        >
          <BadgeCheck className="size-3.5 text-white" strokeWidth={2.5} />
        </span>
      )}
    </div>
  );
}

function RolePill({ role }: { role?: string | null }) {
  const normalized = (role ?? '').toLowerCase();
  const isOwner = normalized === 'owner';
  const isAdmin = normalized === 'admin';

  const palette = isOwner
    ? 'bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300'
    : isAdmin
      ? 'bg-indigo-500/10 text-indigo-700 ring-indigo-500/20 dark:text-indigo-300'
      : 'bg-violet-500/10 text-violet-700 ring-violet-500/20 dark:text-violet-300';

  const Icon = isOwner ? Crown : ShieldCheck;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] ring-1 ring-inset',
        palette,
      )}
    >
      <Icon className="size-3" strokeWidth={2.5} />
      {role ?? 'member'}
    </span>
  );
}

export default function UserSettings() {
  const user = useAuthStore((s) => s.user);
  const initials = getInitials(user?.first_name, user?.last_name) || 'U';
  const fullName =
    [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim() ||
    user?.email ||
    'Your account';

  return (
    <div className="w-full">
      {/* ── Page header (matches the other settings pages) ────── */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">User settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your personal account details and how you appear across the workspace.
        </p>
      </div>

      {/* ── Two-column body ───────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr] lg:items-start">
        {/* ── Left: account summary (sticky) ─────────────────── */}
        <aside className="lg:sticky lg:top-6">
          <section className="relative overflow-hidden rounded-3xl border border-border/70 bg-gradient-to-br from-primary/[0.08] via-card to-card">
            <span
              aria-hidden
              className="pointer-events-none absolute -right-20 -top-20 size-52 rounded-full bg-primary/[0.10] blur-3xl"
            />
            <div className="relative flex flex-col items-center px-6 pb-6 pt-8 text-center">
              <AvatarPreview url={user?.avatar_url} initials={initials} />
              <p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground/80">
                Account
              </p>
              <h2 className="mt-1 max-w-full truncate text-[20px] font-semibold leading-tight tracking-tight text-foreground">
                {fullName}
              </h2>
              <div className="mt-1.5 flex max-w-full items-center gap-1.5 text-sm text-muted-foreground">
                <Mail className="size-3.5 shrink-0" strokeWidth={2.25} />
                <span className="truncate">{user?.email ?? '—'}</span>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                <RolePill role={user?.role} />
                {user?.is_verified && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-emerald-700 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-300">
                    <BadgeCheck className="size-3" strokeWidth={2.5} />
                    Verified
                  </span>
                )}
              </div>
            </div>
          </section>
        </aside>

        {/* ── Right: profile form ────────────────────────────── */}
        <section className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-1">
            <div className="flex items-center gap-2">
              <UserCircle className="size-4 text-primary" strokeWidth={2.25} />
              <h2 className="text-[15px] font-semibold tracking-tight text-foreground">Profile</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              Update your name, avatar, and how teammates see you.
            </p>
          </div>
          <div className="overflow-hidden rounded-3xl border border-border/70 bg-card">
            <ProfileForm />
          </div>
        </section>
      </div>
    </div>
  );
}

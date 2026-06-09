'use client';

import { BadgeCheck, Crown, Mail, ShieldCheck, UserCircle } from 'lucide-react';
import { useState } from 'react';

import { PageHeader } from '@/components/layout/page-header';
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
        {/* Neutral background sits behind the image so transparent PNGs still look intentional */}
        <span aria-hidden className="absolute inset-0 border border-border bg-background" />
        {showImage ? (
          <img
            src={url}
            alt="Avatar preview"
            className="relative size-full object-cover"
            onError={() => setBroken(true)}
          />
        ) : (
          <span className={cn('relative font-semibold text-foreground', labelClass)}>
            {initials}
          </span>
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

  const Icon = isOwner ? Crown : ShieldCheck;

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
      <Icon className="size-3 text-foreground" strokeWidth={2.5} />
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
    <div className="flex min-h-0 flex-1 flex-col">
      {/* ── Fixed page header ─────────────────────────────────── */}
      <header className="shrink-0 border-b border-border/60 bg-background">
        <div className="mx-auto max-w-4xl px-6 py-5">
          <PageHeader
            kicker="User settings"
            title="User settings."
            description="Manage your personal account details and how you appear across the workspace."
          />
        </div>
      </header>

      {/* ── Scrollable content ──────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl space-y-6 px-6 pb-12 pt-6">
          {/* ── Hero / account summary ─────────────────────────── */}
          <section className="group relative overflow-hidden rounded-xl border border-border bg-card p-6 transition-all duration-200 hover:border-foreground/20 sm:p-7">
            <div className="relative flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-6">
              <AvatarPreview url={user?.avatar_url} initials={initials} />
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                  Account
                </p>
                <h2 className="mt-1.5 truncate text-[26px] font-semibold leading-tight tracking-tight text-foreground">
                  {fullName}
                </h2>
                <div className="mt-1.5 flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Mail className="size-3.5" strokeWidth={2.25} />
                  <span className="truncate">{user?.email ?? '—'}</span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <RolePill role={user?.role} />
                  {user?.is_verified && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-emerald-700 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-300">
                      <BadgeCheck className="size-3" strokeWidth={2.5} />
                      Verified
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* hairline accent that wipes in on hover */}
            <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
          </section>

          {/* ── Profile form ───────────────────────────────────── */}
          <section className="space-y-3">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-1">
              <div className="flex items-center gap-2">
                <UserCircle className="size-4 text-primary" strokeWidth={2.25} />
                <h2 className="text-[15px] font-semibold tracking-tight text-foreground">
                  Profile
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                Update your name, avatar, and how teammates see you.
              </p>
            </div>
            <div className="overflow-hidden rounded-xl border border-border bg-card">
              <ProfileForm />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

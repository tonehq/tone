'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useSetAtom } from 'jotai';
import { Asterisk, Lock, Save } from 'lucide-react';
import { useEffect } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { updateProfileAtom } from '@/atoms/UserSettingsAtom';
import { CustomButton, TextInput } from '@/components/shared';
import { getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { AvatarPreview } from './UserSettings';

const profileSchema = z.object({
  first_name: z
    .string()
    .min(1, 'First name is required')
    .max(100, 'First name must be at most 100 characters'),
  last_name: z
    .string()
    .min(1, 'Last name is required')
    .max(100, 'Last name must be at most 100 characters'),
  avatar_url: z
    .string()
    .trim()
    .max(512, 'Avatar URL must be at most 512 characters')
    .url('Enter a valid URL')
    .optional()
    .or(z.literal('')),
});

type ProfileFormData = z.infer<typeof profileSchema>;

function SectionLabel({ index, title, hint }: { index: string; title: string; hint: string }) {
  return (
    <div className="mb-4 flex items-baseline gap-3">
      <span className="text-[10px] font-mono font-semibold tracking-[0.18em] text-muted-foreground/60">
        {index}
      </span>
      <div className="min-w-0">
        <h3 className="text-[13px] font-semibold tracking-tight text-foreground">{title}</h3>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{hint}</p>
      </div>
    </div>
  );
}

export default function ProfileForm() {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useSetAtom(updateProfileAtom);

  const { control, handleSubmit, reset, formState } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      avatar_url: '',
    },
    mode: 'onChange',
  });

  // Watch the avatar URL + name so the swatch preview reflects typing in real time.
  const watchedAvatar = useWatch({ control, name: 'avatar_url' });
  const watchedFirst = useWatch({ control, name: 'first_name' });
  const watchedLast = useWatch({ control, name: 'last_name' });

  useEffect(() => {
    if (!user) return;
    reset({
      first_name: user.first_name ?? '',
      last_name: user.last_name ?? '',
      avatar_url: user.avatar_url ?? '',
    });
  }, [user, reset]);

  const onSubmit = async (data: ProfileFormData) => {
    try {
      await updateProfile({
        first_name: data.first_name.trim(),
        last_name: data.last_name.trim(),
        avatar_url: data.avatar_url?.trim() ? data.avatar_url.trim() : null,
      });
      showToast.success('Profile updated');
    } catch (err) {
      handleApiError(err);
    }
  };

  const saving = formState.isSubmitting;
  const previewInitials =
    getInitials(watchedFirst || user?.first_name, watchedLast || user?.last_name) || 'U';

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* ── Identity ─────────────────────────────────────────── */}
      <div className="p-5 sm:p-6">
        <SectionLabel
          index="01"
          title="Identity"
          hint="Your name and avatar appear in the sidebar, on shared resources, and in audit logs."
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextInput
            name="first_name"
            control={control}
            label="First name"
            placeholder="Jane"
            isRequired
            disabled={saving}
          />
          <TextInput
            name="last_name"
            control={control}
            label="Last name"
            placeholder="Doe"
            isRequired
            disabled={saving}
          />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <TextInput
            name="avatar_url"
            control={control}
            label="Avatar URL"
            placeholder="https://example.com/avatar.png"
            disabled={saving}
            helperText="Paste an image link. Leave blank to use your initials."
          />
          <div className="flex shrink-0 items-center gap-3 rounded-2xl border border-dashed border-border/70 bg-muted/30 px-3 py-2.5 sm:mb-[2px]">
            <AvatarPreview url={watchedAvatar || null} initials={previewInitials} size="sm" />
            <div className="hidden text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground sm:block">
              Preview
            </div>
          </div>
        </div>
      </div>

      {/* ── Divider ──────────────────────────────────────────── */}
      <div className="relative">
        <div className="h-px bg-border/70" />
        <span
          aria-hidden
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/70 bg-card px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/70"
        >
          Read only
        </span>
      </div>

      {/* ── Account ──────────────────────────────────────────── */}
      <div className="p-5 sm:p-6">
        <SectionLabel
          index="02"
          title="Account"
          hint="Managed by your workspace owner. Contact an admin to change these."
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="relative">
            <TextInput
              name="email"
              label="Email"
              value={user?.email ?? ''}
              readOnly
              disabled
              leftIcon={<Lock className="size-3.5 text-muted-foreground/70" />}
            />
          </div>
          <div className="relative">
            <TextInput
              name="role"
              label="Role"
              value={user?.role ?? '—'}
              readOnly
              disabled
              leftIcon={<Lock className="size-3.5 text-muted-foreground/70" />}
            />
          </div>
        </div>
      </div>

      {/* ── Footer / save bar ────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 border-t border-border/70 bg-muted/20 px-5 py-3 sm:px-6">
        <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Asterisk className="size-3 text-rose-500" strokeWidth={3} />
          Required field
        </p>
        <CustomButton
          type="primary"
          onClick={handleSubmit(onSubmit)}
          icon={<Save className="size-4" />}
          loading={saving}
          disabled={!formState.isValid || saving || !formState.isDirty}
        >
          {saving ? 'Saving...' : 'Save changes'}
        </CustomButton>
      </div>
    </form>
  );
}

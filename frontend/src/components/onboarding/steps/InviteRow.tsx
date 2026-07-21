'use client';

import { Trash2 } from 'lucide-react';

import { CustomButton, SelectInput, TextInput } from '@/components/shared';
import { ONBOARDING_INVITE_ROLES } from '@/constants/onboarding';

import type { OnboardingForm } from '../types';

interface InviteRowProps {
  form: OnboardingForm;
  index: number;
  onRemove: () => void;
}

export default function InviteRow({ form, index, onRemove }: InviteRowProps) {
  return (
    <div className="flex items-start gap-2">
      <div className="flex-1">
        <TextInput
          name={`invites.${index}.email`}
          control={form.control}
          type="email"
          placeholder="teammate@company.com"
        />
      </div>
      <div className="w-40">
        <SelectInput
          name={`invites.${index}.role`}
          control={form.control}
          options={ONBOARDING_INVITE_ROLES}
        />
      </div>
      <CustomButton
        type="text"
        onClick={onRemove}
        aria-label="Remove invite"
        className="mt-1 h-9 w-9 p-0 text-muted-foreground hover:text-foreground"
      >
        <Trash2 className="h-4 w-4" />
      </CustomButton>
    </div>
  );
}

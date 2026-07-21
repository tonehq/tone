'use client';

import { useFieldArray } from 'react-hook-form';
import { Plus } from 'lucide-react';

import { CustomButton } from '@/components/shared';

import type { OnboardingForm } from '../types';
import InviteRow from './InviteRow';

interface InvitesStepProps {
  form: OnboardingForm;
}

const EMPTY_ROW = { email: '', role: 'developer' } as const;

export default function InvitesStep({ form }: InvitesStepProps) {
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'invites',
  });

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Invite your teammates</h1>
        <p className="text-sm text-muted-foreground">
          Add anyone who should have access to this workspace. We&apos;ll email them an invite.
        </p>
      </div>
      <div className="space-y-3">
        {fields.map((field, index) => (
          <InviteRow
            key={field.id}
            form={form}
            index={index}
            onRemove={() => {
              if (fields.length === 1) {
                // Never leave the list truly empty — reset the row so the user
                // sees a fresh input rather than a bare "Add another" button.
                form.setValue(`invites.${index}.email`, '');
                form.setValue(`invites.${index}.role`, 'developer');
                return;
              }
              remove(index);
            }}
          />
        ))}
        <CustomButton
          type="text"
          onClick={() => append({ ...EMPTY_ROW })}
          className="h-8 px-2 text-primary"
        >
          <Plus className="mr-1 h-4 w-4" />
          Add another
        </CustomButton>
      </div>
    </div>
  );
}

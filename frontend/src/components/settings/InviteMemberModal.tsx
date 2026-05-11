'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { type InviteMemberFormData, inviteMemberSchema } from '@/schemas/settings';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCallback, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

interface InviteMemberModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; email: string; role: string }) => Promise<void>;
}

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'member', label: 'Member' },
  { value: 'viewer', label: 'Viewer' },
];

function getApiErrorDetail(error: unknown): string {
  if (typeof error === 'object' && error !== null) {
    const detail = (error as any).response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
  }
  return '';
}

export default function InviteMemberModal({ open, onClose, onSubmit }: InviteMemberModalProps) {
  const { control, handleSubmit, reset, setError, formState } = useForm<InviteMemberFormData>({
    resolver: zodResolver(inviteMemberSchema),
    defaultValues: { name: '', email: '' },
  });

  const [role, setRole] = useState('member');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      reset({ name: '', email: '' });
      setRole('member');
    }
  }, [open, reset]);

  const onFormSubmit = useCallback(
    async (data: InviteMemberFormData) => {
      setSaving(true);
      try {
        await onSubmit({ name: data.name.trim(), email: data.email.trim(), role });
        reset({ name: '', email: '' });
        onClose();
      } catch (err) {
        const detail = getApiErrorDetail(err);
        if (detail) {
          setError('email', { message: detail });
        }
      } finally {
        setSaving(false);
      }
    },
    [role, onSubmit, onClose, reset, setError],
  );

  const handleCancel = () => {
    reset({ name: '', email: '' });
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title="Invite Member"
      confirmText="Send Invite"
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid}
    >
      <div className="space-y-4">
        <TextInput
          name="name"
          control={control}
          label="Name"
          placeholder="Enter name"
          isRequired
          disabled={saving}
        />
        <TextInput
          name="email"
          control={control}
          type="email"
          label="Email"
          placeholder="Enter email address"
          isRequired
          disabled={saving}
        />
        <SelectInput
          name="invite-role"
          label="Role"
          options={ROLE_OPTIONS}
          value={role}
          onValueChange={setRole}
          disabled={saving}
        />
      </div>
    </CustomModal>
  );
}

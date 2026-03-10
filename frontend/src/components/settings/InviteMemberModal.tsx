'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { useCallback, useEffect, useState } from 'react';

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

const VALID_ROLES = new Set(ROLE_OPTIONS.map((o) => o.value));

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const initialFormState = { name: '', email: '', role: 'member' };

function getApiErrorDetail(error: unknown): string {
  if (typeof error === 'object' && error !== null) {
    const detail = (error as any).response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
  }
  return '';
}

export default function InviteMemberModal({ open, onClose, onSubmit }: InviteMemberModalProps) {
  const [name, setName] = useState(initialFormState.name);
  const [email, setEmail] = useState(initialFormState.email);
  const [role, setRole] = useState(initialFormState.role);
  const [saving, setSaving] = useState(false);
  const [nameError, setNameError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [roleError, setRoleError] = useState('');

  const resetForm = useCallback(() => {
    setName(initialFormState.name);
    setEmail(initialFormState.email);
    setRole(initialFormState.role);
    setNameError('');
    setEmailError('');
    setRoleError('');
  }, []);

  useEffect(() => {
    if (open) resetForm();
  }, [open, resetForm]);

  const validate = (): boolean => {
    let valid = true;

    if (!name.trim()) {
      setNameError('Please enter a name');
      valid = false;
    } else {
      setNameError('');
    }

    if (!email.trim()) {
      setEmailError('Please enter an email address');
      valid = false;
    } else if (!EMAIL_REGEX.test(email.trim())) {
      setEmailError('Please enter a valid email address');
      valid = false;
    } else {
      setEmailError('');
    }

    if (!VALID_ROLES.has(role)) {
      setRoleError('Please select a valid role');
      valid = false;
    } else {
      setRoleError('');
    }

    return valid;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setSaving(true);
    try {
      await onSubmit({ name: name.trim(), email: email.trim(), role });
      resetForm();
      onClose();
    } catch (err) {
      const detail = getApiErrorDetail(err);
      if (detail) {
        setEmailError(detail);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    onClose();
  };

  const hasErrors = !!nameError || !!emailError || !!roleError;

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title="Invite Member"
      confirmText="Send Invite"
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={hasErrors && saving}
    >
      <div className="space-y-4">
        <div>
          <TextInput
            name="invite-name"
            label="Name"
            placeholder="Enter name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (nameError) setNameError('');
            }}
            disabled={saving}
            error={!!nameError}
            helperText={nameError}
          />
        </div>
        <div>
          <TextInput
            name="invite-email"
            type="email"
            label="Email"
            placeholder="Enter email address"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (emailError) setEmailError('');
            }}
            disabled={saving}
            error={!!emailError}
            helperText={emailError}
          />
        </div>
        <div>
          <SelectInput
            name="invite-role"
            label="Role"
            options={ROLE_OPTIONS}
            value={role}
            onValueChange={(val) => {
              setRole(val);
              if (roleError) setRoleError('');
            }}
            disabled={saving}
            error={!!roleError}
            helperText={roleError}
          />
        </div>
      </div>
    </CustomModal>
  );
}

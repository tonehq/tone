'use client';

import { CustomModal, TextInput } from '@/components/shared';
import type { IntegrationRow } from '@/types/integration';
import { useCallback, useEffect, useState } from 'react';

interface AddChannelModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    id?: number;
    name: string;
    auth_token: string;
    account_sid: string;
  }) => Promise<void>;
  editData?: IntegrationRow | null;
}

const initialFormState = {
  name: '',
  auth_token: '',
  account_sid: '',
};

export default function AddChannelModal({
  open,
  onClose,
  onSubmit,
  editData,
}: AddChannelModalProps) {
  const [name, setName] = useState(initialFormState.name);
  const [auth_token, setAuthToken] = useState(initialFormState.auth_token);
  const [account_sid, setAccountSid] = useState(initialFormState.account_sid);
  const [saving, setSaving] = useState(false);

  const isEdit = Boolean(editData);

  useEffect(() => {
    if (open && editData) {
      setName(editData.name);
      setAuthToken(editData.auth_token);
      setAccountSid(editData.account_sid);
    } else if (open) {
      setName(initialFormState.name);
      setAuthToken(initialFormState.auth_token);
      setAccountSid(initialFormState.account_sid);
    }
  }, [open, editData]);

  const resetForm = useCallback(() => {
    setName(initialFormState.name);
    setAuthToken(initialFormState.auth_token);
    setAccountSid(initialFormState.account_sid);
  }, []);

  const handleSubmit = async () => {
    if (!name.trim() || !auth_token.trim() || !account_sid.trim()) return;
    setSaving(true);
    try {
      await onSubmit({
        ...(editData ? { id: editData.id } : {}),
        name: name.trim(),
        auth_token: auth_token.trim(),
        account_sid: account_sid.trim(),
      });
      resetForm();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title={isEdit ? 'Edit API key' : 'Add new API key'}
      confirmText={saving ? 'Saving...' : 'Save'}
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={!name.trim() || !auth_token.trim() || !account_sid.trim()}
    >
      <div className="space-y-4">
        <div>
          <TextInput
            name="channel-name"
            label="Name"
            placeholder="e.g. Twilio Production"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
          />
        </div>
        <div>
          <TextInput
            name="channel-auth-token"
            label="Auth Token"
            type="password"
            placeholder="Enter auth token"
            value={auth_token}
            onChange={(e) => setAuthToken(e.target.value)}
            disabled={saving}
          />
        </div>
        <div>
          <TextInput
            name="channel-account-sid"
            label="Account SID"
            placeholder="Enter account SID"
            value={account_sid}
            onChange={(e) => setAccountSid(e.target.value)}
            disabled={saving}
          />
        </div>
      </div>
    </CustomModal>
  );
}

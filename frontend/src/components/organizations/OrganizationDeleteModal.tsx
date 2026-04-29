'use client';

import { CustomModal, TextInput } from '@/components/shared';
import { useState } from 'react';

interface OrganizationDeleteModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  organizationName: string;
  loading?: boolean;
}

const OrganizationDeleteModal: React.FC<OrganizationDeleteModalProps> = ({
  open,
  onClose,
  onConfirm,
  organizationName,
  loading = false,
}) => {
  const [confirmName, setConfirmName] = useState('');

  const handleClose = () => {
    setConfirmName('');
    onClose();
  };

  const handleConfirm = async () => {
    await onConfirm();
    setConfirmName('');
  };

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Delete Organization"
      description={`This action is irreversible. All members, invites, and data associated with "${organizationName}" will be permanently deleted.`}
      confirmText="Delete"
      confirmType="danger"
      confirmLoading={loading}
      confirmDisabled={confirmName !== organizationName}
      onConfirm={handleConfirm}
    >
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">
          Type <span className="font-semibold text-foreground">{organizationName}</span> to confirm.
        </p>
        <TextInput
          name="confirm_name"
          placeholder="Organization name"
          value={confirmName}
          onChange={(e) => setConfirmName(e.target.value)}
          autoComplete="off"
        />
      </div>
    </CustomModal>
  );
};

export default OrganizationDeleteModal;

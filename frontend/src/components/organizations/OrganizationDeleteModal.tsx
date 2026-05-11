'use client';

import { CustomModal, TextInput } from '@/components/shared';
import { type OrganizationDeleteFormData, organizationDeleteSchema } from '@/schemas/organization';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

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
  const { control, handleSubmit, reset, watch } = useForm<OrganizationDeleteFormData>({
    resolver: zodResolver(organizationDeleteSchema),
    defaultValues: { confirm_name: '' },
  });

  const confirmName = watch('confirm_name');

  useEffect(() => {
    if (open) reset({ confirm_name: '' });
  }, [open, reset]);

  const handleClose = () => {
    reset({ confirm_name: '' });
    onClose();
  };

  const onFormSubmit = async () => {
    await onConfirm();
    reset({ confirm_name: '' });
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
      onConfirm={handleSubmit(onFormSubmit)}
    >
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">
          Type <span className="font-semibold text-foreground">{organizationName}</span> to confirm.
        </p>
        <TextInput
          name="confirm_name"
          control={control}
          placeholder="Organization name"
          autoComplete="off"
        />
      </div>
    </CustomModal>
  );
};

export default OrganizationDeleteModal;

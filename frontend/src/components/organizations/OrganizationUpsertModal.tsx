'use client';

import { CustomModal, TextAreaField, TextInput } from '@/components/shared';
import type { OrganizationDetails, OrganizationUpdatePayload } from '@/types/organization';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

interface OrganizationFormValues {
  name: string;
  description: string;
  website_url: string;
  logo_url: string;
}

interface OrganizationUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (
    data: { name: string } | { orgId: string; payload: OrganizationUpdatePayload },
  ) => Promise<void>;
  organization?: OrganizationDetails | null;
  loading?: boolean;
}

const OrganizationUpsertModal: React.FC<OrganizationUpsertModalProps> = ({
  open,
  onClose,
  onSubmit,
  organization,
  loading = false,
}) => {
  const isEdit = !!organization;

  const { control, handleSubmit, reset } = useForm<OrganizationFormValues>({
    defaultValues: {
      name: '',
      description: '',
      website_url: '',
      logo_url: '',
    },
  });

  useEffect(() => {
    if (open) {
      if (organization) {
        reset({
          name: organization.name,
          description: organization.description ?? '',
          website_url: organization.website_url ?? '',
          logo_url: organization.logo_url ?? '',
        });
      } else {
        reset({ name: '', description: '', website_url: '', logo_url: '' });
      }
    }
  }, [open, organization, reset]);

  const handleFormSubmit = handleSubmit(async (values) => {
    if (isEdit && organization) {
      const payload: OrganizationUpdatePayload = {};
      if (values.name !== organization.name) payload.name = values.name;
      if (values.description !== (organization.description ?? ''))
        payload.description = values.description;
      if (values.website_url !== (organization.website_url ?? ''))
        payload.website_url = values.website_url;
      if (values.logo_url !== (organization.logo_url ?? '')) payload.logo_url = values.logo_url;

      await onSubmit({ orgId: organization.id, payload });
    } else {
      await onSubmit({ name: values.name });
    }
  });

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Organization' : 'Create Organization'}
      description={
        isEdit
          ? 'Update organization details.'
          : 'Create a new organization. You will be added as the owner.'
      }
      confirmText={isEdit ? 'Save' : 'Create'}
      confirmLoading={loading}
      onConfirm={handleFormSubmit}
      width="sm:max-w-lg"
    >
      <div className="flex flex-col gap-4">
        <TextInput
          name="name"
          label="Name"
          placeholder="Organization name"
          control={control}
          rules={{ required: 'Name is required' }}
          isRequired
        />
        {isEdit && (
          <>
            <TextAreaField
              name="description"
              label="Description"
              placeholder="Brief description of the organization"
              control={control}
              rows={3}
            />
            <TextInput
              name="website_url"
              label="Website"
              placeholder="https://example.com"
              control={control}
            />
            <TextInput
              name="logo_url"
              label="Logo URL"
              placeholder="https://cdn.example.com/logo.png"
              control={control}
            />
          </>
        )}
      </div>
    </CustomModal>
  );
};

export default OrganizationUpsertModal;

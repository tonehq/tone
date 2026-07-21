'use client';

import { CustomModal, TextAreaField, TextInput, TimezoneSelect } from '@/components/shared';
import { type OrganizationUpsertFormData, organizationUpsertSchema } from '@/schemas/organization';
import type { OrganizationDetails, OrganizationUpdatePayload } from '@/types/organization';
import { getBrowserTimeZone } from '@/utils/date';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

interface OrganizationUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (
    data:
      | { name: string; schedulingTimezone?: string }
      | { orgId: string; payload: OrganizationUpdatePayload },
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

  // Default scheduling timezone (org `settings` JSONB, saved via `/organization/details`).
  // Editable for any org the user manages: on edit it's prefilled from the fetched org, on
  // create it defaults to the browser zone and is sent through the create endpoint.
  const [schedulingTz, setSchedulingTz] = useState<string>('');
  const [initialTz, setInitialTz] = useState<string>('');

  const { control, handleSubmit, reset, formState } = useForm<OrganizationUpsertFormData>({
    resolver: zodResolver(organizationUpsertSchema),
    defaultValues: {
      name: '',
      description: '',
      website_url: '',
      logo_url: '',
    },
  });

  useEffect(() => {
    if (!open) return;
    if (organization) {
      reset({
        name: organization.name,
        description: organization.description ?? '',
        website_url: organization.website_url ?? '',
        logo_url: organization.logo_url ?? '',
      });
      const tz = organization.scheduling_timezone || getBrowserTimeZone();
      setSchedulingTz(tz);
      setInitialTz(tz);
    } else {
      reset({ name: '', description: '', website_url: '', logo_url: '' });
      setSchedulingTz(getBrowserTimeZone());
      setInitialTz('');
    }
  }, [open, organization, reset]);

  const onFormSubmit = async (values: OrganizationUpsertFormData) => {
    if (isEdit && organization) {
      const payload: OrganizationUpdatePayload = {};
      if (values.name !== organization.name) payload.name = values.name;
      if ((values.description ?? '') !== (organization.description ?? ''))
        payload.description = values.description;
      if ((values.website_url ?? '') !== (organization.website_url ?? ''))
        payload.website_url = values.website_url;
      if ((values.logo_url ?? '') !== (organization.logo_url ?? ''))
        payload.logo_url = values.logo_url;
      // Persist the scheduling timezone through the same /details update when it changed.
      if (schedulingTz && schedulingTz !== initialTz) {
        payload.scheduling_timezone = schedulingTz;
      }

      await onSubmit({ orgId: organization.id, payload });
    } else {
      // Create: the timezone is optional and sent through the create endpoint.
      await onSubmit({ name: values.name, schedulingTimezone: schedulingTz || undefined });
    }
  };

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
      confirmDisabled={!formState.isValid}
      onConfirm={handleSubmit(onFormSubmit)}
      width="sm:max-w-lg"
    >
      <div className="flex flex-col gap-4">
        <TextInput
          name="name"
          label="Name"
          placeholder="Organization name"
          control={control}
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
        <div className="flex flex-col gap-1.5">
          <TimezoneSelect
            name="scheduling_timezone"
            label="Default scheduling timezone"
            value={schedulingTz}
            onValueChange={setSchedulingTz}
          />
          <p className="text-xs text-muted-foreground">
            Optional. Used as the default timezone when scheduling outbound calls; defaults to your
            browser timezone.
          </p>
        </div>
      </div>
    </CustomModal>
  );
};

export default OrganizationUpsertModal;

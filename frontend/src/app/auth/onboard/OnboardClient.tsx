'use client';

import { useCallback, useState } from 'react';
import { useFieldArray, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { debounce } from 'lodash';
import { useRouter } from 'next/navigation';
import { Plus, Trash2 } from 'lucide-react';

import Container from '@/app/auth/shared/ContainerComponent';
import { CustomButton, TextInput, SelectInput } from '@/components/shared';
import { type OnboardOrgFormData, onboardOrgSchema } from '@/schemas/auth';
import { createOrganization } from '@/services/organizationService';
import { setToken } from '@/services/auth/helper';
import { switchOrganization } from '@/services/organizationService';
import { inviteUserToOrganization } from '@/services/userService';
import axios from '@/utils/axios';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const ROLE_OPTIONS = [
  { label: 'Member', value: 'member' },
  { label: 'Admin', value: 'admin' },
];

interface InviteRow {
  email: string;
  role: string;
}

const OnboardClient = () => {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loader, setLoader] = useState(false);
  const [orgExists, setOrgExists] = useState(false);

  // Step 1 form
  const { control: orgControl, handleSubmit: handleOrgSubmit } = useForm<OnboardOrgFormData>({
    resolver: zodResolver(onboardOrgSchema),
    defaultValues: { org_name: '' },
  });

  // Step 2 form
  const { control: inviteControl, handleSubmit: handleInviteSubmit } = useForm<{
    invites: InviteRow[];
  }>({
    defaultValues: { invites: [{ email: '', role: 'member' }] },
  });

  const { fields, append, remove } = useFieldArray({
    control: inviteControl,
    name: 'invites',
  });

  const checkOrgExists = useCallback(
    debounce(async (orgName: string) => {
      if (!orgName || orgName.trim().length < 2) {
        setOrgExists(false);
        return;
      }
      try {
        const res = await axios.get(
          `/auth/check_organization_exists?name=${encodeURIComponent(orgName.trim())}`,
        );
        setOrgExists(res.data.exists === true);
      } catch {
        setOrgExists(false);
      }
    }, 500),
    [],
  );

  const onOrgSubmit = async (values: OnboardOrgFormData) => {
    if (orgExists) {
      showToast.warning(
        'Organization Exists',
        'An organization with this name already exists. Please choose a different name.',
        5,
      );
      return;
    }

    setLoader(true);
    try {
      const created = await createOrganization(values.org_name.trim());
      // Switch to the newly created org so API calls in step 2 use the right tenant
      const switchRes = await switchOrganization(created.id);
      const tokenData = {
        ...switchRes,
        organizations: switchRes.organization ? [switchRes.organization] : [],
      };
      await setToken(tokenData);
      setStep(2);
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoader(false);
    }
  };

  const onInviteSubmit = async (values: { invites: InviteRow[] }) => {
    const validInvites = values.invites.filter((inv) => inv.email.trim());
    if (validInvites.length === 0) {
      router.push('/home');
      return;
    }

    setLoader(true);
    try {
      await Promise.all(
        validInvites.map((inv) =>
          inviteUserToOrganization({
            name: inv.email.split('@')[0],
            email: inv.email.trim(),
            role: inv.role,
          }),
        ),
      );
      showToast.success('Invitations Sent', 'Your team members will receive an email shortly.', 3);
      router.push('/home');
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoader(false);
    }
  };

  const handleSkip = () => {
    router.push('/home');
  };

  return (
    <Container>
      <div className="w-full max-w-[440px] animate-page">
        {/* Step indicator */}
        <div className="mb-6 flex items-center gap-2">
          <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-primary' : 'bg-muted'}`} />
          <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-primary' : 'bg-muted'}`} />
        </div>
        <p className="mb-6 text-xs text-muted-foreground">Step {step} of 2</p>

        {step === 1 && (
          <>
            <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
              Create your workspace
            </h2>
            <p className="mb-8 text-sm text-muted-foreground">
              Give your organization a name to get started.
            </p>

            <form onSubmit={handleOrgSubmit(onOrgSubmit)} autoComplete="off" className="space-y-5">
              <TextInput
                name="org_name"
                control={orgControl}
                type="text"
                label="Organisation name"
                placeholder="e.g. Acme Inc."
                isRequired
                onValueChange={(value) => checkOrgExists(value)}
              />
              {orgExists && (
                <p className="text-xs text-destructive">
                  An organization with this name already exists.
                </p>
              )}

              <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
                Continue
              </CustomButton>
            </form>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
              Invite your team
            </h2>
            <p className="mb-8 text-sm text-muted-foreground">
              Add team members to collaborate on your voice agents.
            </p>

            <form
              onSubmit={handleInviteSubmit(onInviteSubmit)}
              autoComplete="off"
              className="space-y-4"
            >
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-start gap-2">
                  <div className="flex-1">
                    <TextInput
                      name={`invites.${index}.email`}
                      control={inviteControl}
                      type="email"
                      placeholder="colleague@company.com"
                    />
                  </div>
                  <div className="w-28">
                    <SelectInput
                      name={`invites.${index}.role`}
                      control={inviteControl}
                      options={ROLE_OPTIONS}
                      placeholder="Role"
                    />
                  </div>
                  {fields.length > 1 && (
                    <CustomButton
                      type="text"
                      htmlType="button"
                      className="mt-1 shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={() => remove(index)}
                    >
                      <Trash2 size={16} />
                    </CustomButton>
                  )}
                </div>
              ))}

              <CustomButton
                type="text"
                htmlType="button"
                className="text-sm text-primary"
                onClick={() => append({ email: '', role: 'member' })}
                icon={<Plus size={14} />}
              >
                Add another
              </CustomButton>

              <div className="flex items-center justify-between pt-2">
                <CustomButton
                  type="text"
                  htmlType="button"
                  className="text-sm text-muted-foreground"
                  onClick={handleSkip}
                >
                  Skip for now
                </CustomButton>
                <CustomButton loading={loader} type="primary" htmlType="submit">
                  Send Invites
                </CustomButton>
              </div>
            </form>
          </>
        )}
      </div>
    </Container>
  );
};

export default OnboardClient;

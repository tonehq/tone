'use client';

import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { Building2, CheckCircle, LogIn, XCircle } from 'lucide-react';

import { acceptInviteSchema, type AcceptInviteFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Button } from '@/components/ui/button';
import { CustomCard, Form, PageLoader, TextInput } from '@/components/shared';
import { useAcceptInvitation, useValidateInvitation } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

function AcceptInviteContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';
  const { user, setLoginResponse } = useAuthStore();

  const { data: invitation, isLoading, error } = useValidateInvitation(token);
  const acceptInvitation = useAcceptInvitation();

  const { control, handleSubmit } = useForm<AcceptInviteFormData>({
    resolver: zodResolver(acceptInviteSchema),
    defaultValues: { first_name: '', last_name: '', password: '', confirm_password: '' },
  });

  const onSubmitNewUser = async (values: AcceptInviteFormData) => {
    try {
      const result = await acceptInvitation.mutateAsync({
        token,
        password: values.password,
        first_name: values.first_name,
        last_name: values.last_name,
      });
      if (result.access_token) setLoginResponse(result);
      await queryClient.invalidateQueries();
      showToast.success('Welcome!', 'Your account has been created.');
      router.push('/home');
    } catch (err) {
      handleApiError(err);
    }
  };

  const onAcceptAsExistingUser = async () => {
    try {
      await acceptInvitation.mutateAsync({ token });
      await queryClient.invalidateQueries();
      showToast.success(
        'Joined!',
        invitation
          ? `You're now a member of ${invitation.organization_name}.`
          : 'You joined the workspace.',
      );
      router.push('/home');
    } catch (err) {
      handleApiError(err);
    }
  };

  if (!token) {
    return (
      <CustomCard
        centered
        icon={<XCircle className="h-12 w-12 text-destructive" />}
        title="Invalid invitation"
        description="No invitation token provided."
        contentClassName="pt-0 text-center"
      >
        <Link href="/login">
          <Button>Go to login</Button>
        </Link>
      </CustomCard>
    );
  }

  if (isLoading) {
    return <PageLoader message="Validating invitation..." />;
  }

  if (error || !invitation?.valid) {
    const errorMessage =
      (error as any)?.response?.data?.detail || 'This invitation is invalid or has expired.';
    return (
      <CustomCard
        centered
        icon={<XCircle className="h-12 w-12 text-destructive" />}
        title="Invalid invitation"
        description={errorMessage}
        contentClassName="pt-0 text-center"
      >
        <Link href="/login">
          <Button>Go to login</Button>
        </Link>
      </CustomCard>
    );
  }

  if (user) {
    return (
      <CustomCard
        centered
        icon={
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
        }
        title={`Join ${invitation.organization_name}`}
        description={`You're signed in as ${user.email}. Accept this invite to join as ${invitation.role}.`}
      >
        <Button
          className="w-full"
          loading={acceptInvitation.isPending}
          onClick={onAcceptAsExistingUser}
        >
          Accept invitation
        </Button>
      </CustomCard>
    );
  }

  if (invitation.account_exists) {
    return (
      <CustomCard
        centered
        icon={
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
            <LogIn className="h-6 w-6 text-primary" />
          </div>
        }
        title={`Join ${invitation.organization_name}`}
        description={`Sign in to accept this invitation as a ${invitation.role}.`}
      >
        <Link href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}>
          <Button className="w-full">Sign in to continue</Button>
        </Link>
      </CustomCard>
    );
  }

  return (
    <CustomCard
      centered
      icon={
        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
          <CheckCircle className="h-6 w-6 text-primary" />
        </div>
      }
      title={`Join ${invitation.organization_name}`}
      description={`You've been invited to join as a ${invitation.role}. Create your account below.`}
    >
      <Form handleSubmit={handleSubmit} onSubmit={onSubmitNewUser}>
        <TextInput name="email" label="Email" value={invitation.email} disabled />
        <div className="grid grid-cols-2 gap-4">
          <TextInput name="first_name" control={control} label="First name" isRequired />
          <TextInput name="last_name" control={control} label="Last name" isRequired />
        </div>
        <TextInput name="password" control={control} label="Password" type="password" isRequired />
        <TextInput
          name="confirm_password"
          control={control}
          label="Confirm password"
          type="password"
          isRequired
        />
        <Button type="submit" className="w-full" loading={acceptInvitation.isPending}>
          Create account &amp; join
        </Button>
      </Form>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link
          href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}
          className="text-primary hover:underline"
        >
          Sign in
        </Link>
      </p>
    </CustomCard>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <AcceptInviteContent />
    </Suspense>
  );
}

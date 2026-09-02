'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';

import { acceptInviteSchema, type AcceptInviteFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { AppLoader, CustomButton, Form } from '@/components/shared';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthResult, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useAcceptInvitation, useValidateInvitation } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

function StaticField({ label, value }: { label: string; value: string }) {
  return (
    <div className="pt-6">
      <span className="block text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <p className="border-b border-border pb-2.5 pt-1.5 text-[15px] text-muted-foreground">
        {value}
      </p>
    </div>
  );
}

function AcceptInviteContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || searchParams.get('code') || '';
  const { user, setLoginResponse } = useAuthStore();
  const [accepted, setAccepted] = useState(false);

  const { data: invitation, isLoading, error } = useValidateInvitation(token, !accepted);
  const acceptInvitation = useAcceptInvitation();

  const { control, handleSubmit } = useForm<AcceptInviteFormData>({
    resolver: zodResolver(acceptInviteSchema),
    defaultValues: { first_name: '', last_name: '', password: '', confirm_password: '' },
  });

  const handleAcceptResult = (result: Awaited<ReturnType<typeof acceptInvitation.mutateAsync>>) => {
    if (result?.access_token) {
      setLoginResponse(result);
      showToast.success(
        'Joined!',
        invitation
          ? `You're now a member of ${invitation.organization_name}.`
          : 'You joined the workspace.',
      );
      router.push('/home');
      return;
    }
    showToast.success(
      'Added to workspace',
      invitation
        ? `Please sign in to access ${invitation.organization_name}.`
        : 'Please sign in to continue.',
    );
    router.push('/login');
  };

  const refreshUserState = async () => {
    setAccepted(true);
    queryClient.cancelQueries({ queryKey: ['invitation', token] });
    await queryClient.invalidateQueries({
      predicate: (q) => q.queryKey?.[0] !== 'invitation',
    });
  };

  const onSubmitNewUser = async (values: AcceptInviteFormData) => {
    try {
      const result = await acceptInvitation.mutateAsync({
        token,
        password: values.password,
        first_name: values.first_name,
        last_name: values.last_name,
      });
      await refreshUserState();
      handleAcceptResult(result);
    } catch (err) {
      handleApiError(err);
    }
  };

  const onAcceptAsExistingUser = async () => {
    try {
      const result = await acceptInvitation.mutateAsync({ token });
      await refreshUserState();
      handleAcceptResult(result);
    } catch (err) {
      handleApiError(err);
    }
  };

  if (!token) {
    return (
      <AuthResult
        tone="error"
        title="Invalid invitation."
        description="No invitation token was provided."
      >
        <Link href="/login">
          <CustomButton type="default" fullWidth className="h-11">
            Go to sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  if (isLoading) {
    return <AppLoader label="Validating invitation..." />;
  }

  if (error || !invitation?.valid) {
    const errorMessage =
      (error as any)?.response?.data?.detail || 'This invitation is invalid or has expired.';
    return (
      <AuthResult tone="error" title="Invalid invitation." description={errorMessage}>
        <Link href="/login">
          <CustomButton type="default" fullWidth className="h-11">
            Go to sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  if (user) {
    return (
      <AuthResult
        title={`Join ${invitation.organization_name}.`}
        description={`You're signed in as ${user.email}. Accept this invite to join as ${invitation.role}.`}
      >
        <CustomButton
          type="primary"
          fullWidth
          className="h-11"
          loading={acceptInvitation.isPending}
          onClick={onAcceptAsExistingUser}
        >
          Accept invitation
        </CustomButton>
      </AuthResult>
    );
  }

  if (invitation.account_exists) {
    return (
      <AuthResult
        title={`Join ${invitation.organization_name}.`}
        description={`${invitation.email} already has a Tone account. Accept to add it to ${invitation.organization_name}, then sign in.`}
      >
        <div className="flex flex-col gap-2.5">
          <CustomButton
            type="primary"
            fullWidth
            className="h-11"
            loading={acceptInvitation.isPending}
            onClick={onAcceptAsExistingUser}
          >
            Accept invitation
          </CustomButton>
          <Link href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}>
            <CustomButton type="default" fullWidth className="h-11" htmlType="button">
              Sign in first
            </CustomButton>
          </Link>
        </div>
      </AuthResult>
    );
  }

  return (
    <>
      <AuthHeading
        title={`Join ${invitation.organization_name}.`}
        subtitle={`You've been invited as a ${invitation.role}. Create your account to continue.`}
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmitNewUser} className="space-y-7">
        <motion.div variants={fadeUp}>
          <StaticField label="Email address" value={invitation.email} />
        </motion.div>

        <motion.div className="grid grid-cols-2 gap-5" variants={fadeUp}>
          <AuthField
            name="first_name"
            control={control}
            label="First name"
            autoComplete="given-name"
          />
          <AuthField
            name="last_name"
            control={control}
            label="Last name"
            autoComplete="family-name"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="password"
            control={control}
            type="password"
            label="Password"
            autoComplete="new-password"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="confirm_password"
            control={control}
            type="password"
            label="Confirm password"
            autoComplete="new-password"
          />
        </motion.div>

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={acceptInvitation.isPending}>Create account &amp; join</AuthSubmit>
        </motion.div>
      </Form>

      <motion.p className="mt-8 text-center text-[13px] text-muted-foreground" variants={fadeUp}>
        Already have an account?{' '}
        <Link
          href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}
          className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        >
          Sign in
        </Link>
      </motion.p>
    </>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<AppLoader />}>
      <AcceptInviteContent />
    </Suspense>
  );
}

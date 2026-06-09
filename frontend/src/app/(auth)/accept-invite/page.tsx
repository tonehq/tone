'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

import { acceptInviteSchema, type AcceptInviteFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { AppLoader, CustomButton, Form } from '@/components/shared';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthResult, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useAcceptInvitation, useValidateInvitation } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

function AcceptInviteContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  // `code` is the legacy query name (older invite emails). Accept either.
  const token = searchParams.get('token') || searchParams.get('code') || '';
  const { user, setLoginResponse } = useAuthStore();
  // Stop revalidating once the user has consumed the invite — otherwise the
  // post-accept refresh refetches the now-accepted token and returns 400.
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
    // Anonymous accept for an existing account — server added the membership
    // but didn't issue tokens. Redirect to login so the user can sign in
    // and pick up the new workspace.
    showToast.success(
      'Added to workspace',
      invitation
        ? `Please sign in to access ${invitation.organization_name}.`
        : 'Please sign in to continue.',
    );
    router.push('/login');
  };

  const refreshUserState = async () => {
    // Mark accepted FIRST so useValidateInvitation flips to enabled=false
    // before we touch the cache — otherwise React Query refetches the now-
    // consumed token and returns 400.
    setAccepted(true);
    queryClient.cancelQueries({ queryKey: ['invitation', token] });
    // Refresh the rest of the cache (me, my-org, etc.) so the next page sees
    // the new membership immediately.
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
        code="ERR"
        kicker="Invitation"
        title="Invalid invitation."
        description="No invitation token was provided in this link."
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
    return <AppLoader label="Validating invitation…" />;
  }

  if (error || !invitation?.valid) {
    const errorMessage =
      (error as any)?.response?.data?.detail || 'This invitation is invalid or has expired.';
    return (
      <AuthResult
        tone="error"
        code="ERR"
        kicker="Invitation"
        title="Invalid invitation."
        description={errorMessage}
      >
        <Link href="/login">
          <CustomButton type="default" fullWidth className="h-11">
            Go to sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  // Already signed in — one-click accept.
  if (user) {
    return (
      <>
        <AuthHeading
          index="05"
          kicker="Invitation"
          title={`Join ${invitation.organization_name}.`}
          subtitle={
            <>
              You're signed in as <strong className="text-foreground">{user.email}</strong>. Accept
              to join as {invitation.role}.
            </>
          }
        />
        <CustomButton
          type="primary"
          fullWidth
          loading={acceptInvitation.isPending}
          onClick={onAcceptAsExistingUser}
          className="group h-11 text-[14px]"
        >
          Accept invitation
          <ArrowRight className="ml-1 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
        </CustomButton>
      </>
    );
  }

  // Existing account, not signed in.
  if (invitation.account_exists) {
    return (
      <>
        <AuthHeading
          index="05"
          kicker="Invitation"
          title={`Join ${invitation.organization_name}.`}
          subtitle={
            <>
              <strong className="text-foreground">{invitation.email}</strong> already has a Tone
              account. Accept to add it to {invitation.organization_name}, then sign in.
            </>
          }
        />
        <div className="flex flex-col gap-3">
          <CustomButton
            type="primary"
            fullWidth
            loading={acceptInvitation.isPending}
            onClick={onAcceptAsExistingUser}
            className="group h-11 text-[14px]"
          >
            Accept invitation
            <ArrowRight className="ml-1 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
          </CustomButton>
          <Link href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}>
            <CustomButton type="default" fullWidth htmlType="button" className="h-11">
              Sign in first
            </CustomButton>
          </Link>
        </div>
      </>
    );
  }

  // New user — create an account to join.
  return (
    <>
      <AuthHeading
        index="05"
        kicker="Invitation"
        title={`Join ${invitation.organization_name}.`}
        subtitle={`You've been invited as a ${invitation.role}. Create your account below.`}
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmitNewUser} className="space-y-7">
        <motion.div variants={fadeUp}>
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Email
          </div>
          <div className="mt-1 border-b border-border pb-2.5 text-[15px] text-foreground/60">
            {invitation.email}
          </div>
        </motion.div>

        <motion.div className="grid grid-cols-2 gap-5" variants={fadeUp}>
          <AuthField name="first_name" control={control} label="First name" index="A1" />
          <AuthField name="last_name" control={control} label="Last name" index="A2" />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="password"
            control={control}
            type="password"
            label="Password"
            autoComplete="new-password"
            index="A3"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="confirm_password"
            control={control}
            type="password"
            label="Confirm password"
            autoComplete="new-password"
            index="A4"
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

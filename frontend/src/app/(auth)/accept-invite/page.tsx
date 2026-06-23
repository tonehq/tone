'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { Building2, CheckCircle, LogIn, LogOut, XCircle } from 'lucide-react';

import { acceptInviteSchema, type AcceptInviteFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Button } from '@/components/ui/button';
import { AppLoader, CustomCard, Form, TextInput } from '@/components/shared';
import { useAcceptInvitation, useValidateInvitation } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

function AcceptInviteContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  // `code` is the legacy query name (older invite emails). Accept either.
  const token = searchParams.get('token') || searchParams.get('code') || '';
  const { user, setLoginResponse, clearAuth } = useAuthStore();
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
    return <AppLoader label="Validating invitation..." />;
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
    // Backend rejects accept when the logged-in user's email doesn't match
    // invite.email (403). Catch the mismatch in the UI so the user gets a
    // clear next step ("log out") instead of clicking Accept and getting a
    // confusing 403 toast. clearAuth() resets the store and the page falls
    // through to the account_exists / new-account branch below.
    const emailMismatch =
      !!user.email &&
      !!invitation.email &&
      user.email.toLowerCase() !== invitation.email.toLowerCase();

    if (emailMismatch) {
      return (
        <CustomCard
          centered
          icon={
            <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <XCircle className="h-6 w-6 text-destructive" />
            </div>
          }
          title="Wrong account"
          description={`This invitation was sent to ${invitation.email}, but you're signed in as ${user.email}. Log out and sign in with the invited account to accept it.`}
        >
          <Button
            className="w-full"
            variant="outline"
            type="button"
            onClick={() => {
              clearAuth();
              // Drop cached me/org queries so anything pre-fetched under the
              // previous identity is gone before the page re-renders.
              queryClient.removeQueries({
                predicate: (q) => q.queryKey?.[0] !== 'invitation',
              });
            }}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </Button>
        </CustomCard>
      );
    }

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
        description={`${invitation.email} already has a Tone account. Accept to add it to ${invitation.organization_name}, then sign in.`}
      >
        <div className="flex flex-col gap-2">
          <Button
            className="w-full"
            loading={acceptInvitation.isPending}
            onClick={onAcceptAsExistingUser}
          >
            Accept invitation
          </Button>
          <Link href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`}>
            <Button variant="outline" className="w-full" type="button">
              Sign in first
            </Button>
          </Link>
        </div>
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
    <Suspense fallback={<AppLoader />}>
      <AcceptInviteContent />
    </Suspense>
  );
}

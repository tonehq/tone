'use client';

import { CustomButton, TextInput } from '@/components/shared';
import { Form } from '@/components/shared/Form';
import { acceptInvitationWithPassword, validateInvitation } from '@/services/userService';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useCallback, useEffect, useState } from 'react';

import Container from '../../auth/shared/ContainerComponent';

interface InviteInfo {
  valid: boolean;
  email: string;
  name: string;
  role: string;
  user_exists: boolean;
}

function AcceptInvitationContent() {
  const [loader, setLoader] = useState(false);
  const [validating, setValidating] = useState(true);
  const [inviteInfo, setInviteInfo] = useState<InviteInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const params = useSearchParams();

  const email = params?.get('email') ?? '';
  const code = params?.get('code') ?? '';

  const validateOnMount = useCallback(async () => {
    if (!email || !code) {
      setError('Invalid invitation link. Missing email or code.');
      setValidating(false);
      return;
    }

    try {
      const result = await validateInvitation(email, code);
      if (result.user_exists) {
        showToast.info(
          'Account exists',
          'You already have an account. Please login to accept the invitation.',
        );
        router.push('/auth/login');
        return;
      }
      setInviteInfo(result);
    } catch {
      setError('This invitation is invalid or has expired.');
    } finally {
      setValidating(false);
    }
  }, [email, code, router]);

  useEffect(() => {
    validateOnMount();
  }, [validateOnMount]);

  const handleSubmit = async (value: Record<string, string>) => {
    if (!value['password'] || !value['confirm_password']) return;

    if (value['password'] !== value['confirm_password']) {
      showToast.error('Passwords do not match');
      return;
    }

    if (value['password'].length < 8) {
      showToast.error('Password must be at least 8 characters');
      return;
    }

    setLoader(true);
    try {
      await acceptInvitationWithPassword({
        email,
        code,
        password: value['password'].trim(),
      });
      showToast.success(
        'Account Created',
        'Your account has been created successfully. Please login.',
      );
      setTimeout(() => {
        router.push('/auth/login');
      }, 2000);
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoader(false);
    }
  };

  if (validating) {
    return (
      <Container>
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Validating invitation...</p>
        </div>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <div className="w-full max-w-[400px] animate-page text-center">
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
            Invalid Invitation
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">{error}</p>
          <CustomButton type="primary" onClick={() => router.push('/auth/login')} fullWidth>
            Go to Login
          </CustomButton>
        </div>
      </Container>
    );
  }

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page">
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Set Your Password
        </h2>
        <p className="mb-8 text-sm text-muted-foreground">
          Welcome, {inviteInfo?.name}! Set a password to create your account and join as{' '}
          <span className="font-medium capitalize">{inviteInfo?.role}</span>.
        </p>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <div className="space-y-5">
            <TextInput
              name="password"
              type="password"
              label="Password"
              placeholder="Enter password"
              isRequired
            />
            <TextInput
              name="confirm_password"
              type="password"
              label="Confirm Password"
              placeholder="Confirm password"
              isRequired
            />

            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Create Account
            </CustomButton>
          </div>
        </Form>
      </div>
    </Container>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={null}>
      <AcceptInvitationContent />
    </Suspense>
  );
}

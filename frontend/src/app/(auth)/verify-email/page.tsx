'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

import { showToast } from '@/lib/toast';
import { AppLoader, CustomButton } from '@/components/shared';
import { AuthResult } from '@/components/auth/auth-ui';
import { useVerifyEmail } from '@/lib/api/auth';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const mutation = useVerifyEmail();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    if (!token) {
      setStatus('error');
      setErrorMsg('Invalid verification link');
      return;
    }
    startedRef.current = true;

    mutation
      .mutateAsync(token)
      .then(() => {
        setStatus('success');
        showToast.success('Email verified successfully!');
      })
      .catch((err: unknown) => {
        setStatus('error');
        const detail = (err as any)?.response?.data?.detail || 'Verification failed';
        setErrorMsg(detail);
        showToast.error(detail);
      });
  }, [token]);

  if (status === 'loading') {
    return <AppLoader label="Verifying your email..." />;
  }

  if (status === 'success') {
    return (
      <AuthResult
        tone="success"
        title="Email verified."
        description="You're all set. Let's finish setting up your workspace."
      >
        <Link href="/onboarding">
          <CustomButton type="primary" fullWidth className="h-11">
            Continue to onboarding
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  return (
    <AuthResult tone="error" title="Verification failed." description={errorMsg}>
      <Link href="/login">
        <CustomButton type="default" fullWidth className="h-11">
          Back to sign in
        </CustomButton>
      </Link>
    </AuthResult>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<AppLoader />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

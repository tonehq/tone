'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

import { showToast } from '@/lib/toast';
import { AppLoader, CustomButton } from '@/components/shared';
import { AuthResult, AuthSubmit } from '@/components/auth/auth-ui';
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
    return <AppLoader label="Verifying your email…" className="animate-page" />;
  }

  if (status === 'success') {
    return (
      <AuthResult
        tone="success"
        code="OK"
        kicker="Verified"
        title="You're all set."
        description="Your email is verified. Sign in to start building voice agents."
      >
        <Link href="/login">
          <AuthSubmit>Go to sign in</AuthSubmit>
        </Link>
      </AuthResult>
    );
  }

  return (
    <AuthResult
      tone="error"
      code="ERR"
      kicker="Verification"
      title="That link didn't work."
      description={errorMsg}
    >
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
    <Suspense fallback={<AppLoader className="animate-page" />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

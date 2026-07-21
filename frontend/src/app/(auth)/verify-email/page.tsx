'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, XCircle } from 'lucide-react';

import { showToast } from '@/lib/toast';
import { AppLoader } from '@/components/shared';
import { Button } from '@/components/ui/button';
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
    return <AppLoader label="Verifying your email..." className="animate-page" />;
  }

  if (status === 'success') {
    return (
      <div className="animate-page text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold">Email Verified!</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your email is verified. Let&apos;s finish setting up your workspace.
        </p>
        <Link href="/onboarding">
          <Button className="mt-6">Continue to Onboarding</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-page text-center">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
        <XCircle className="h-8 w-8 text-red-600" />
      </div>
      <h2 className="text-2xl font-bold">Verification Failed</h2>
      <p className="mt-2 text-sm text-muted-foreground">{errorMsg}</p>
      <div className="mt-6 space-x-3">
        <Link href="/login">
          <Button variant="outline">Back to Login</Button>
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<AppLoader className="animate-page" />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

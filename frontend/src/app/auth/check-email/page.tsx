'use client';

import { Mail } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

const CheckEmailContent = () => {
  const params = useSearchParams();
  const email = params.get('email') || 'your email';

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="max-w-[400px] rounded-[5px] bg-white p-6 text-center shadow-md">
        {/* Icon */}
        <div className="mx-auto mb-3 flex size-20 items-center justify-center rounded-full bg-violet-500/10">
          <Mail size={40} className="text-violet-500" />
        </div>

        {/* Title */}
        <h4 className="mb-2 text-xl font-semibold">Check your email</h4>

        {/* Description */}
        <div className="mb-4">
          <p className="mb-1 text-[15px] text-muted-foreground">We&apos;ve sent an email to</p>
          <p className="text-[15px] font-semibold">{email}</p>
          <p className="mt-1 text-[15px] text-muted-foreground">
            Click the link in the email to verify your account.
          </p>
        </div>

        {/* Footer note */}
        <p className="text-sm text-muted-foreground">
          Didn&apos;t receive the email? Check your spam folder or{' '}
          <Link href="/auth/login" className="font-medium text-indigo-500 hover:underline">
            try again
          </Link>
        </p>
      </div>
    </div>
  );
};

const CheckEmailPage = () => (
  <Suspense fallback={null}>
    <CheckEmailContent />
  </Suspense>
);

export default CheckEmailPage;

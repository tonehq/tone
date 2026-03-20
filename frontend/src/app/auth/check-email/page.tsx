'use client';

import { Mail } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

import { CustomLink } from '@/components/shared';
import Container from '../shared/ContainerComponent';

const CheckEmailContent = () => {
  const params = useSearchParams();
  const email = params.get('email') || 'your email';

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page text-center">
        {/* Icon */}
        <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary/10">
          <Mail className="size-8 text-primary" />
        </div>

        {/* Title */}
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Check your email
        </h2>

        {/* Description */}
        <div className="mb-6">
          <p className="mb-1 text-sm text-muted-foreground">We&apos;ve sent an email to</p>
          <p className="text-sm font-semibold text-foreground">{email}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Click the link in the email to verify your account.
          </p>
        </div>

        {/* Footer note */}
        <p className="text-sm text-muted-foreground">
          Didn&apos;t receive the email? Check your spam folder or{' '}
          <CustomLink href="/auth/login">try again</CustomLink>
        </p>
      </div>
    </Container>
  );
};

const CheckEmailPage = () => (
  <Suspense fallback={null}>
    <CheckEmailContent />
  </Suspense>
);

export default CheckEmailPage;

'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';

import { loginSchema, type LoginFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, CustomButton } from '@/components/shared';
import { Checkbox } from '@/components/ui/primitives';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useLogin, useResendVerification } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get('next');
  const login = useLogin();
  const resend = useResendVerification();
  const setLoginResponse = useAuthStore((s) => s.setLoginResponse);

  const { control, handleSubmit, watch } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const email = watch('email');
  const needsVerification =
    login.isError &&
    (login.error as any)?.response?.data?.detail?.toString().toLowerCase().includes('verify');

  const onSubmit = async (values: LoginFormData) => {
    try {
      const data = await login.mutateAsync(values);
      setLoginResponse(data);
      showToast.success('Welcome back!');
      const needsOnboarding = data.organization?.onboarding_completed === false;
      const safeNext = nextPath && nextPath.startsWith('/') ? nextPath : '/home';
      router.push(needsOnboarding ? '/onboarding' : safeNext);
    } catch (err) {
      handleApiError(err);
    }
  };

  const handleResendVerification = async () => {
    try {
      await resend.mutateAsync(email);
      showToast.success('Verification email sent!');
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <>
      <AuthHeading title="Welcome back." subtitle="Sign in to pick up where you left off." />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="space-y-7">
        <motion.div variants={fadeUp}>
          <AuthField
            name="email"
            control={control}
            type="email"
            label="Email address"
            autoComplete="email"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="password"
            control={control}
            type="password"
            label="Password"
            autoComplete="current-password"
          />
        </motion.div>

        <motion.div className="flex items-center justify-between pt-1" variants={fadeUp}>
          <label className="flex cursor-pointer select-none items-center gap-2 text-[13px] text-foreground/75">
            <Checkbox id="remember" />
            <span>Keep me signed in</span>
          </label>
          <Link
            href="/forgot-password"
            className="text-[13px] font-medium text-primary underline-offset-4 transition-colors hover:text-primary/80 hover:underline"
          >
            Forgot password?
          </Link>
        </motion.div>

        {needsVerification && (
          <motion.div
            className="rounded-lg border border-warning/30 bg-warning/10 p-3.5 text-sm text-foreground"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
          >
            <p className="text-[13px]">Please verify your email before signing in.</p>
            <CustomButton
              type="link"
              htmlType="button"
              onClick={handleResendVerification}
              disabled={!email}
              loading={resend.isPending}
              className="mt-1 h-auto p-0 font-medium"
            >
              Resend verification email
            </CustomButton>
          </motion.div>
        )}

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={login.isPending}>Sign in</AuthSubmit>
        </motion.div>
      </Form>

      <motion.div
        className="mt-8 flex flex-col items-center gap-2 text-[13px] text-muted-foreground"
        variants={fadeUp}
      >
        <Link
          href="/sign-in-with-code"
          className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        >
          Sign in with a code instead
        </Link>
        <p>
          New to Tone?{' '}
          <Link
            href="/signup"
            className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
          >
            Create an account
          </Link>
        </p>
      </motion.div>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageInner />
    </Suspense>
  );
}

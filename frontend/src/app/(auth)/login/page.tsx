'use client';

import { Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';

import { loginSchema, type LoginFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, TextInput } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/primitives';
import { useLogin, useResendVerification } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  },
};

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
      const safeNext = nextPath && nextPath.startsWith('/') ? nextPath : '/home';
      router.push(safeNext);
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
      <motion.div className="mb-8" variants={fadeUp}>
        <h2 className="font-display text-[28px] font-semibold tracking-tight">Welcome back</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Enter your credentials to access your account
        </p>
      </motion.div>
      <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
        <motion.div variants={fadeUp}>
          <TextInput
            name="email"
            control={control}
            type="email"
            label="Email"
            placeholder="you@company.com"
            isRequired
          />
        </motion.div>
        <motion.div className="space-y-2" variants={fadeUp}>
          <label htmlFor="password" className="text-sm font-medium leading-none">
            Password
          </label>
          <TextInput name="password" control={control} type="password" placeholder="••••••••" />
        </motion.div>

        <motion.div className="flex items-center justify-between" variants={fadeUp}>
          <label className="flex cursor-pointer items-center gap-2 text-[13px] text-foreground/80">
            <Checkbox id="remember" />
            <span>Remember me</span>
          </label>
          <Link
            href="/forgot-password"
            className="text-[13px] font-medium text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </motion.div>

        {needsVerification && (
          <motion.div
            className="rounded-md bg-yellow-50 p-3 text-sm text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200"
            variants={fadeUp}
          >
            <p>Please verify your email before logging in.</p>
            <Button
              variant="link"
              type="button"
              onClick={handleResendVerification}
              disabled={!email}
              loading={resend.isPending}
              className="mt-1 h-auto p-0 font-medium"
            >
              Resend verification email
            </Button>
          </motion.div>
        )}

        <motion.div variants={fadeUp}>
          <Button type="submit" className="w-full" loading={login.isPending}>
            Sign In
          </Button>
        </motion.div>
      </Form>
      <motion.p className="mt-6 text-center text-sm text-muted-foreground" variants={fadeUp}>
        Don&apos;t have an account?{' '}
        <Link href="/signup" className="font-medium text-primary hover:underline">
          Sign up
        </Link>
      </motion.p>
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

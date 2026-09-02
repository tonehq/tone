'use client';

import { useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';

import { resetPasswordSchema, type ResetPasswordFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { AppLoader, Form, CustomButton } from '@/components/shared';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthResult, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useResetPassword } from '@/lib/api/auth';

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const mutation = useResetPassword();

  const { control, handleSubmit } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirm_password: '' },
  });

  useEffect(() => {
    if (!token) {
      showToast.error('Invalid reset link');
      router.push('/forgot-password');
    }
  }, [token, router]);

  const onSubmit = async (values: ResetPasswordFormData) => {
    try {
      await mutation.mutateAsync({ token: token!, new_password: values.password });
      showToast.success('Password reset successfully');
    } catch (err) {
      handleApiError(err);
    }
  };

  if (mutation.isSuccess) {
    return (
      <AuthResult
        tone="success"
        title="Password updated."
        description="Your password has been reset. You can sign in with it now."
      >
        <Link href="/login">
          <CustomButton type="primary" fullWidth className="h-11">
            Sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  if (!token) return null;

  return (
    <>
      <AuthHeading
        title="Set a new password."
        subtitle="Choose something you haven't used before."
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="space-y-7">
        <motion.div variants={fadeUp}>
          <AuthField
            name="password"
            control={control}
            type="password"
            label="New password"
            autoComplete="new-password"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="confirm_password"
            control={control}
            type="password"
            label="Confirm password"
            autoComplete="new-password"
          />
        </motion.div>

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={mutation.isPending}>Reset password</AuthSubmit>
        </motion.div>
      </Form>

      <motion.p className="mt-8 text-center text-[13px] text-muted-foreground" variants={fadeUp}>
        <Link
          href="/login"
          className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        >
          Back to sign in
        </Link>
      </motion.p>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<AppLoader />}>
      <ResetPasswordContent />
    </Suspense>
  );
}

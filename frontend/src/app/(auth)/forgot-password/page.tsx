'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';

import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/schemas/auth';
import { showToast } from '@/lib/toast';
import { Form, CustomButton } from '@/components/shared';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthResult, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useForgotPassword } from '@/lib/api/auth';

export default function ForgotPasswordPage() {
  const mutation = useForgotPassword();

  const { control, handleSubmit, watch } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const email = watch('email');

  const onSubmit = async (values: ForgotPasswordFormData) => {
    await mutation.mutateAsync(values.email);
    showToast.success('Reset link sent if the email exists');
  };

  if (mutation.isSuccess) {
    return (
      <AuthResult
        tone="info"
        code="SENT"
        kicker="Reset access"
        title="Check your inbox."
        description={
          <>
            If an account exists for <strong className="text-foreground">{email}</strong>, a reset
            link is on its way.
          </>
        }
      >
        <Link href="/login">
          <CustomButton type="default" fullWidth className="h-11">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  return (
    <>
      <AuthHeading
        index="03"
        kicker="Reset access"
        title="Forgot password?"
        subtitle="Enter your email and we'll send a link to reset it."
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="space-y-7">
        <motion.div variants={fadeUp}>
          <AuthField
            name="email"
            control={control}
            type="email"
            label="Email address"
            autoComplete="email"
            index="A1"
          />
        </motion.div>

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={mutation.isPending}>Send reset link</AuthSubmit>
        </motion.div>
      </Form>

      <motion.div className="mt-8 text-center" variants={fadeUp}>
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to sign in
        </Link>
      </motion.div>
    </>
  );
}

'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';

import { signupSchema, type SignupFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, CustomButton } from '@/components/shared';
import { AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthResult, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useSignup } from '@/lib/api/auth';

export default function SignupPage() {
  const signup = useSignup();

  const { control, handleSubmit, watch } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      password: '',
    },
  });

  const email = watch('email');

  const onSubmit = async (values: SignupFormData) => {
    try {
      await signup.mutateAsync(values);
      showToast.success('Account created!', 'Check your email to verify.', 4);
    } catch (err) {
      handleApiError(err);
    }
  };

  if (signup.isSuccess) {
    return (
      <AuthResult
        tone="info"
        title="Check your inbox."
        description={
          <>
            We sent a verification link to <strong className="text-foreground">{email}</strong>.
            Open it to activate your account and start building.
          </>
        }
      >
        <Link href="/login">
          <CustomButton type="default" fullWidth className="h-11">
            Back to sign in
          </CustomButton>
        </Link>
      </AuthResult>
    );
  }

  return (
    <>
      <AuthHeading
        title="Start building."
        subtitle="Spin up your first voice agent in a few minutes."
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="space-y-7">
        <motion.div className="grid grid-cols-2 gap-5" variants={fadeUp}>
          <AuthField
            name="first_name"
            control={control}
            label="First name"
            autoComplete="given-name"
          />
          <AuthField
            name="last_name"
            control={control}
            label="Last name"
            autoComplete="family-name"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="email"
            control={control}
            type="email"
            label="Work email"
            autoComplete="email"
          />
        </motion.div>

        <motion.div variants={fadeUp}>
          <AuthField
            name="password"
            control={control}
            type="password"
            label="Password"
            autoComplete="new-password"
          />
        </motion.div>

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={signup.isPending}>Create account</AuthSubmit>
        </motion.div>
      </Form>

      <motion.p className="mt-8 text-center text-[13px] text-muted-foreground" variants={fadeUp}>
        Already have an account?{' '}
        <Link
          href="/login"
          className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        >
          Sign in
        </Link>
      </motion.p>
    </>
  );
}

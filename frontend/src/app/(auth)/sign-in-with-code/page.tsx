'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';

import {
  SIGNIN_CODE_LENGTH,
  requestSignInCodeSchema,
  verifySignInCodeSchema,
  type RequestSignInCodeFormData,
  type VerifySignInCodeFormData,
} from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, CustomButton } from '@/components/shared';
import { AuthCodeField, AuthField } from '@/components/auth/auth-field';
import { AuthHeading, AuthSubmit, fadeUp } from '@/components/auth/auth-ui';
import { useRequestSignInCode, useVerifySignInCode } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

const RESEND_COOLDOWN_SECONDS = 60;

function RequestStep({ onSubmitted }: { onSubmitted: (email: string) => void }) {
  const requestCode = useRequestSignInCode();
  const { control, handleSubmit } = useForm<RequestSignInCodeFormData>({
    resolver: zodResolver(requestSignInCodeSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (values: RequestSignInCodeFormData) => {
    try {
      await requestCode.mutateAsync({ email: values.email });
      showToast.success('If the email exists, a code has been sent');
      onSubmitted(values.email);
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <>
      <AuthHeading
        title="Sign in with a code."
        subtitle={`We'll email you a ${SIGNIN_CODE_LENGTH}-digit code. No password needed.`}
      />

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

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={requestCode.isPending}>Send code</AuthSubmit>
        </motion.div>
      </Form>

      <motion.p className="mt-8 text-center text-[13px] text-muted-foreground" variants={fadeUp}>
        <Link
          href="/login"
          className="font-medium text-foreground underline-offset-4 transition-colors hover:underline"
        >
          Sign in with password instead
        </Link>
      </motion.p>
    </>
  );
}

function VerifyStep({ email, onBack }: { email: string; onBack: () => void }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get('next');
  const setLoginResponse = useAuthStore((s) => s.setLoginResponse);

  const requestCode = useRequestSignInCode();
  const verifyCode = useVerifySignInCode();

  const [resendIn, setResendIn] = useState(RESEND_COOLDOWN_SECONDS);

  useEffect(() => {
    if (resendIn <= 0) return;
    const id = window.setTimeout(() => setResendIn((s) => s - 1), 1000);
    return () => window.clearTimeout(id);
  }, [resendIn]);

  const { control, handleSubmit, setValue } = useForm<VerifySignInCodeFormData>({
    resolver: zodResolver(verifySignInCodeSchema),
    defaultValues: { code: '' },
  });

  const onSubmit = async (values: VerifySignInCodeFormData) => {
    try {
      const data = await verifyCode.mutateAsync({ email, code: values.code });
      setLoginResponse(data);
      showToast.success('Welcome back!');
      const safeNext = nextPath && nextPath.startsWith('/') ? nextPath : '/home';
      router.push(safeNext);
    } catch (err) {
      handleApiError(err);
    }
  };

  const onResend = useCallback(async () => {
    if (resendIn > 0) return;
    try {
      await requestCode.mutateAsync({ email });
      setResendIn(RESEND_COOLDOWN_SECONDS);
      setValue('code', '');
      showToast.success('A new code has been sent');
    } catch (err) {
      handleApiError(err);
    }
  }, [email, requestCode, resendIn, setValue]);

  return (
    <>
      <AuthHeading
        title="Enter your code."
        subtitle={
          <>
            We sent a {SIGNIN_CODE_LENGTH}-digit code to{' '}
            <strong className="text-foreground">{email}</strong>. It expires in 10 minutes.
          </>
        }
      />

      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="space-y-7">
        <motion.div variants={fadeUp}>
          <AuthCodeField
            name="code"
            control={control}
            label={`${SIGNIN_CODE_LENGTH}-digit code`}
            length={SIGNIN_CODE_LENGTH}
          />
        </motion.div>

        <motion.div variants={fadeUp} className="pt-1">
          <AuthSubmit loading={verifyCode.isPending}>Verify and sign in</AuthSubmit>
        </motion.div>
      </Form>

      <motion.div className="mt-8 flex items-center justify-between text-[13px]" variants={fadeUp}>
        <CustomButton
          type="link"
          htmlType="button"
          onClick={onBack}
          className="h-auto p-0 text-muted-foreground"
          icon={<ArrowLeft className="h-3.5 w-3.5" />}
        >
          Use a different email
        </CustomButton>
        <CustomButton
          type="link"
          htmlType="button"
          onClick={onResend}
          disabled={resendIn > 0 || requestCode.isPending}
          loading={requestCode.isPending}
          className="h-auto p-0 font-medium"
        >
          {resendIn > 0 ? `Resend in ${resendIn}s` : 'Resend code'}
        </CustomButton>
      </motion.div>
    </>
  );
}

function SignInWithCodeInner() {
  const [email, setEmail] = useState('');
  return email ? (
    <VerifyStep email={email} onBack={() => setEmail('')} />
  ) : (
    <RequestStep onSubmitted={setEmail} />
  );
}

export default function SignInWithCodePage() {
  return (
    <Suspense fallback={null}>
      <SignInWithCodeInner />
    </Suspense>
  );
}

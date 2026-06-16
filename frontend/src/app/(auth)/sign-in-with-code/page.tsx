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
import { Form, TextInput } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { useRequestSignInCode, useVerifySignInCode } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
  },
};

const RESEND_COOLDOWN_SECONDS = 60;
const digitsOnly = (raw: string) => raw.replace(/\D/g, '').slice(0, SIGNIN_CODE_LENGTH);

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
      <motion.div className="mb-8" variants={fadeUp}>
        <h2 className="text-[28px] font-semibold tracking-tight">Sign in with a code</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We&apos;ll email you a {SIGNIN_CODE_LENGTH}-digit code to sign in. No password needed.
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
        <motion.div variants={fadeUp}>
          <Button type="submit" className="w-full" loading={requestCode.isPending}>
            Send code
          </Button>
        </motion.div>
      </Form>
      <motion.p className="mt-6 text-center text-sm text-muted-foreground" variants={fadeUp}>
        <Link href="/login" className="font-medium text-primary hover:underline">
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
      <motion.div className="mb-8" variants={fadeUp}>
        <h2 className="text-[28px] font-semibold tracking-tight">Enter your code</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We sent a {SIGNIN_CODE_LENGTH}-digit code to <strong>{email}</strong>. It expires in 10
          minutes.
        </p>
      </motion.div>
      <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
        <motion.div variants={fadeUp}>
          <TextInput
            name="code"
            control={control}
            type="text"
            label={`${SIGNIN_CODE_LENGTH}-digit code`}
            placeholder="123456"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={SIGNIN_CODE_LENGTH}
            isRequired
            onValueChange={(value) => setValue('code', digitsOnly(value))}
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <Button type="submit" className="w-full" loading={verifyCode.isPending}>
            Verify and sign in
          </Button>
        </motion.div>
      </Form>
      <motion.div className="mt-6 flex items-center justify-between text-sm" variants={fadeUp}>
        <Button
          variant="link"
          type="button"
          onClick={onBack}
          className="h-auto p-0 text-muted-foreground"
        >
          <ArrowLeft className="mr-1 h-3 w-3" />
          Use a different email
        </Button>
        <Button
          variant="link"
          type="button"
          onClick={onResend}
          disabled={resendIn > 0 || requestCode.isPending}
          loading={requestCode.isPending}
          className="h-auto p-0 font-medium"
        >
          {resendIn > 0 ? `Resend in ${resendIn}s` : 'Resend code'}
        </Button>
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

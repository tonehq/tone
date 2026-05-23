'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, MailCheck } from 'lucide-react';

import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/schemas/auth';
import { showToast } from '@/lib/toast';
import { Form, TextInput } from '@/components/shared';
import { Button } from '@/components/ui/button';
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
      <div className="animate-page text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <MailCheck className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">Check your email</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We&apos;ve sent a password reset link to <strong>{email}</strong>
        </p>
        <Link href="/login">
          <Button variant="outline" className="mt-6" icon={<ArrowLeft className="h-4 w-4" />}>
            Back to login
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-page">
      <h2 className="text-[28px] font-semibold tracking-tight">Reset password</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Enter your email and we&apos;ll send you a reset link
      </p>
      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="mt-6">
        <TextInput name="email" control={control} label="Email" type="email" isRequired />
        <Button type="submit" className="w-full" loading={mutation.isPending}>
          Send Reset Link
        </Button>
      </Form>
      <Link
        href="/login"
        className="mt-4 inline-flex items-center text-sm text-primary hover:underline"
      >
        <ArrowLeft className="mr-1 h-3 w-3" />
        Back to login
      </Link>
    </div>
  );
}

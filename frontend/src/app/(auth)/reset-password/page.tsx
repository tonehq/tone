'use client';

import { useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, CheckCircle } from 'lucide-react';

import { resetPasswordSchema, type ResetPasswordFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, PageLoader, TextInput } from '@/components/shared';
import { Button } from '@/components/ui/button';
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
      <div className="animate-page text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold">Password Reset!</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your password has been reset successfully.
        </p>
        <Link href="/login">
          <Button className="mt-6">Sign In</Button>
        </Link>
      </div>
    );
  }

  if (!token) return null;

  return (
    <div className="animate-page">
      <h2 className="font-display text-[28px] font-semibold tracking-tight">Set new password</h2>
      <p className="mt-2 text-sm text-muted-foreground">Enter your new password below</p>
      <Form handleSubmit={handleSubmit} onSubmit={onSubmit} className="mt-6">
        <TextInput
          name="password"
          control={control}
          label="New Password"
          type="password"
          placeholder="Min. 8 characters"
          isRequired
        />
        <TextInput
          name="confirm_password"
          control={control}
          label="Confirm Password"
          type="password"
          placeholder="Confirm your password"
          isRequired
        />
        <Button type="submit" className="w-full" loading={mutation.isPending}>
          Reset Password
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<PageLoader size="md" className="animate-page" />}>
      <ResetPasswordContent />
    </Suspense>
  );
}

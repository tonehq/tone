'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { CustomButton, TextInput } from '@/components/shared';
import { type ResetPasswordFormData, resetPasswordSchema } from '@/schemas/auth';
import axiosInstance from '@/utils/axios';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import Container from '../shared/ContainerComponent';

const ResetPasswordContent = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const params = useSearchParams();

  const { control, handleSubmit } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirm_password: '' },
  });

  const onSubmit = async (values: ResetPasswordFormData) => {
    setLoader(true);
    try {
      const res = await axiosInstance.get(
        `auth/acceptForgotPassword?email=${params?.get('email')}&password=${values.password.trim()}&token=${params?.get('token')}`,
      );
      if (res) {
        showToast.success('Password Reset', 'Your password has been updated successfully', 4);
        setTimeout(() => {
          router.push('/auth/login');
        }, 2000);
      }
      setLoader(false);
    } catch (error) {
      handleApiError(error);
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page">
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Reset password
        </h2>
        <p className="mb-8 text-sm text-muted-foreground">Enter your new password below</p>

        <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
          <TextInput
            name="password"
            control={control}
            type="password"
            label="New Password"
            placeholder="Enter new password"
            isRequired
          />
          <TextInput
            name="confirm_password"
            control={control}
            type="password"
            label="Confirm Password"
            placeholder="Confirm new password"
            isRequired
          />

          <div className="space-y-3">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Reset Password
            </CustomButton>
          </div>
        </form>
      </div>
    </Container>
  );
};

const ResetPasswordPage = () => (
  <Suspense fallback={null}>
    <ResetPasswordContent />
  </Suspense>
);

export default ResetPasswordPage;

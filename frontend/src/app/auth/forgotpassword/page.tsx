'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { CustomButton, CustomLink, TextInput } from '@/components/shared';
import { type ForgotPasswordFormData, forgotPasswordSchema } from '@/schemas/auth';
import { forgotPassword } from '@/services/auth/helper';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import Container from '../shared/ContainerComponent';

const ForgotPasswordPage = () => {
  const [loader, setLoader] = useState(false);

  const { control, handleSubmit } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (values: ForgotPasswordFormData) => {
    setLoader(true);
    try {
      const res = await forgotPassword(values.email);
      if (res) {
        showToast.success('Email Sent', 'Password reset instructions sent to your email', 4);
        setLoader(false);
      }
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
        <p className="mb-8 text-sm text-muted-foreground">
          If there&apos;s an account associated with this email, we will send you a link to reset
          your password.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
          <TextInput
            name="email"
            control={control}
            type="email"
            label="Email"
            placeholder="Enter your email"
            isRequired
          />

          <div className="space-y-3">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Reset Password
            </CustomButton>
            <CustomButton type="default" fullWidth onClick={() => window.history.back()}>
              Cancel
            </CustomButton>
          </div>

          <div className="flex items-center justify-center gap-1">
            <span className="text-sm text-muted-foreground">Remember your password?</span>
            <CustomLink href="/auth/login">Log in</CustomLink>
          </div>
        </form>
      </div>
    </Container>
  );
};

export default ForgotPasswordPage;

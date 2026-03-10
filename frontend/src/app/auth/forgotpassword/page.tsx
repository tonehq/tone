'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import CustomButton from '../../../components/shared/CustomButton';
import TextInput from '../../../components/shared/TextInput';
import { type ForgotPasswordFormData, forgotPasswordSchema } from '../../../schemas/auth';
import { forgotPassword } from '../../../services/auth/helper';
import { handleApiError } from '../../../utils/helpers';
import { showToast } from '../../../utils/toast';
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
      <div className="w-full max-w-[400px]">
        <h4 className="mb-1 text-xl font-semibold">Reset password</h4>
        <p className="mb-4 text-[15px] text-muted-foreground">
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

          <div className="mt-2 flex flex-col gap-2">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Reset Password
            </CustomButton>
            <CustomButton type="default" fullWidth onClick={() => window.history.back()}>
              Cancel
            </CustomButton>
          </div>
        </form>
      </div>
    </Container>
  );
};

export default ForgotPasswordPage;

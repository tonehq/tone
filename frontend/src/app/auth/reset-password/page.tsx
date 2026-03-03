'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/Form';
import TextInput from '../../../components/shared/TextInput';
import axiosInstance from '../../../utils/axios';
import { showToast } from '../../../utils/toast';
import Container from '../shared/ContainerComponent';

const ResetPasswordContent = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const params = useSearchParams();

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (
      value['password'] &&
      value['confirm_password'] &&
      value['password'] === value['confirm_password']
    ) {
      try {
        const res = await axiosInstance.get(
          `api/v1/auth/acceptForgotPassword?email=${params?.get('email')}&password=${value['password'].trim()}&token=${params?.get('token')}`,
        );
        if (res) {
          showToast.success('Password Reset', 'Your password has been updated successfully', 4);
          setTimeout(() => {
            router.push('/auth/login');
          }, 2000);
        }
        setLoader(false);
      } catch (error) {
        let errorMessage = '';

        if (
          typeof error === 'object' &&
          error !== null &&
          'response' in error &&
          'data' in (error as any).response &&
          'detail' in (error as any).response.data
        ) {
          errorMessage = (error as any).response.data.detail;
        }
        showToast.error('Reset Failed', errorMessage || 'Something went wrong', 5);

        setLoader(false);
      }
    } else {
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px]">
        <h4 className="mb-1 text-xl font-semibold">Reset password</h4>
        <p className="mb-4 text-[15px] text-muted-foreground">Enter your new password below</p>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <TextInput
            name="password"
            type="password"
            label="New Password"
            placeholder="Enter new password"
            isRequired
          />
          <TextInput
            name="confirm_password"
            type="password"
            label="Confirm Password"
            placeholder="Confirm new password"
            isRequired
          />

          <div className="mt-2 flex flex-col gap-2">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Reset Password
            </CustomButton>
          </div>
        </Form>
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

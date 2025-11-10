'use client';

import { useEffect, useRef, useState } from 'react';

import { Box, Stack, Typography } from '@mui/material';
import { useRouter, useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

const ResetPasswordContent: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const router = useRouter();
  const [loader, setLoader] = useState(false);
  const params = useSearchParams();
  const { notify, contextHolder } = useNotification();

  useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (
      value['password'] &&
      value['confirm_password'] &&
      value['password'] === value['confirm_password']
    ) {
      try {
        const res = await axios.get(
          `/auth/acceptForgotPassword?email=${params?.get('email')}&password=${value['password'].trim()}&token=${params?.get('token')}`,
        );
        if (res) {
          notify.success(
            'Password Reset',
            'Your password has been updated successfully',
            4,
            'bottomRight',
          );
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
        notify.error('Reset Failed', errorMessage || 'Something went wrong', 5, 'bottomRight');

        setLoader(false);
      }
    } else {
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box>
        <Typography variant="h2" sx={{ mb: 4 }}>
          Reset password
        </Typography>
        <Form
          onFinish={handleSubmit}
          sx={{ width: 400, fontSize: '16px' }}
          layout="vertical"
          autoComplete="off"
        >
          <TextInput
            name="password"
            type="password"
            label="Password"
            placeholder="Enter your password"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
          />
          <TextInput
            name="confirm_password"
            type="password"
            label="Confirm Password"
            placeholder="Enter your confirm password"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
          />
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Update New Password"
              loading={loader}
              type="primary"
              htmlType="submit"
              sx={{ width: '100%' }}
            />
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

const ResetPassword: React.FC = () => <ResetPasswordContent />;

export default ResetPassword;

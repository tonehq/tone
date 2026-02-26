'use client';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/Form';
import TextInput from '../../../components/shared/TextInput';
import axiosInstance from '../../../utils/axios';
import { useNotification } from '../../../utils/notification';
import Container from '../shared/ContainerComponent';

const ResetPasswordContent = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const params = useSearchParams();
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();
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
          notify.success('Password Reset', 'Your password has been updated successfully', 4);
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
        notify.error('Reset Failed', errorMessage || 'Something went wrong', 5);

        setLoader(false);
      }
    } else {
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box sx={{ width: '100%', maxWidth: 400 }}>
        <Typography variant="h4" sx={{ mb: 1, fontWeight: 600 }}>
          Reset password
        </Typography>
        <Typography variant="body1" sx={{ mb: 4, color: theme.palette.text.secondary }}>
          Enter your new password below
        </Typography>

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

          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Reset Password"
              loading={loader}
              type="primary"
              htmlType="submit"
              fullWidth
            />
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

const ResetPasswordPage = () => (
  <Suspense fallback={null}>
    <ResetPasswordContent />
  </Suspense>
);

export default ResetPasswordPage;

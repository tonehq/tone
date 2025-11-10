'use client';

import { useEffect, useRef, useState } from 'react';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import Link from 'next/link';

import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';

import { forgotPassword } from '@/services/auth/helper';

import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

export default function ForgotPassword() {
  const [isLoading, setIsLoading] = useState(true);
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [loader, setLoader] = useState(false);
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();

  useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (value['email']) {
      try {
        const res: any = await forgotPassword(value['email']);
        if (res) {
          notify.success(
            'Email Sent',
            'Password reset instructions sent to your email',
            4,
            'bottomRight',
          );
          setLoader(false);
        }
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
        notify.error('Request Failed', errorMessage || 'Something went wrong', 5, 'bottomRight');
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
          Password Reset Request
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary', mb: 3 }}>
          Enter your email to reset your password.
        </Typography>
        <Form
          onFinish={handleSubmit}
          sx={{ width: 400, fontSize: '16px' }}
          layout="vertical"
          autoComplete="off"
        >
          <TextInput
            name="email"
            type="email"
            label="Email"
            placeholder="Enter Your Email"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
          />
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Request"
              loading={loader}
              type="primary"
              htmlType="submit"
              sx={{ width: '100%' }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Typography
                component={Link}
                href="/auth/login"
                sx={{
                  fontWeight: 500,
                  fontSize: '16px',
                  color: theme.palette.primary.main,
                  cursor: 'pointer',
                  textDecoration: 'none',
                  '&:hover': {
                    textDecoration: 'underline',
                  },
                }}
              >
                Back to Login
              </Typography>
            </Box>
          </Stack>
        </Form>
      </Box>
    </Container>
  );
}

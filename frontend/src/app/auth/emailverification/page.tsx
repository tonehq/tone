'use client';

import { useState } from 'react';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { Form } from '@/components/shared/FormComponent';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

const EmailVerificationContent: React.FC = () => {
  const params = useSearchParams();
  const [loader, setLoader] = useState(false);
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      await axios.get(`/auth/resend_verification_email?email=${params?.get('email')?.trim()}`);
      notify.success('Email Sent', 'Verification email resent successfully', 4, 'bottomRight');
    } catch (error) {
      setLoader(false);
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
      notify.error('Resend Failed', errorMessage || 'Something went wrong', 5, 'bottomRight');
    } finally {
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box>
        <Typography variant="h2" sx={{ mb: 4 }}>
          Thanks for Signing up!
        </Typography>
        <Form
          onFinish={handleSubmit}
          sx={{ width: 400, fontSize: '16px' }}
          layout="vertical"
          autoComplete="off"
        >
          <Box sx={{ marginBottom: 3 }}>
            <Typography variant="body1">
              Please check your email. In a few moments, you will receive a verification email to
              confirm your account.
            </Typography>
          </Box>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Resend"
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
                Back to Signin
              </Typography>
            </Box>
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

const EmailVerification: React.FC = () => <EmailVerificationContent />;

export default EmailVerification;

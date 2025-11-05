'use client';

import { useState } from 'react';

import { Box, Stack } from '@mui/material';
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
      <div>
        <h2 className="mb-8">Thanks for Signing up!</h2>
        <Form
          onFinish={handleSubmit}
          className="w-[400px] text-[16px]"
          layout="vertical"
          autoComplete="off"
        >
          <Box sx={{ marginBottom: 3 }}>
            <p>
              Please check your email. In a few moments, you will receive a verification email to
              confirm your account.
            </p>
          </Box>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Resend"
              loading={loader}
              type="primary"
              htmlType="submit"
              className="w-full"
            />
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Box
                component="div"
                sx={{
                  fontWeight: 500,
                  fontSize: '16px',
                  color: '#4058ff',
                }}
              >
                <Link href="/auth/login" className="cursor-pointer">
                  Back to Signin
                </Link>
              </Box>
            </Box>
          </Stack>
        </Form>
      </div>
    </Container>
  );
};

const EmailVerification: React.FC = () => <EmailVerificationContent />;

export default EmailVerification;

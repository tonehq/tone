'use client';

import { useState } from 'react';

import { Box, Stack } from '@mui/material';
import { useRouter, useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { Form } from '@/components/shared/FormComponent';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

const EmailVerificationContent = () => {
  const [loader, setLoader] = useState(false);
  const params = useSearchParams();
  const router = useRouter();
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get(
        `/auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}`,
      );
      setLoader(false);
      if (res) {
        notify.success(
          'Email Verified',
          'Your email has been verified successfully',
          4,
          'bottomRight',
        );
        router.push('/auth/login');
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
      notify.error(
        'Verification Failed',
        errorMessage || 'Invalid verification link',
        5,
        'bottomRight',
      );
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <div>
        <h2 className="mb-8">Email Verification</h2>
        <Form
          onFinish={handleSubmit}
          className="w-[400px] text-[16px]"
          layout="vertical"
          autoComplete="off"
        >
          <Box sx={{ marginBottom: 3 }}>
            <p>To complete the verification process, please click the button below:</p>
          </Box>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Accept"
              loading={loader}
              type="primary"
              htmlType="submit"
              className="w-full"
            />
          </Stack>
        </Form>
      </div>
    </Container>
  );
};

const EmailVerification: React.FC = () => <EmailVerificationContent />;

export default EmailVerification;

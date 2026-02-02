'use client';

import { Suspense, useState } from 'react';

import CustomButton from '@/components/Shared/CustomButton';
import { Form } from '@/components/Shared/FormComponent';
import axios from '@/utils/axios';
import { useNotification } from '@/utils/notification';
import { Box, Stack, Typography } from '@mui/material';
import { useRouter, useSearchParams } from 'next/navigation';
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
        );
        const inviteRedirect = localStorage.getItem('invite_redirect');
        if (inviteRedirect) {
          localStorage.removeItem('invite_redirect');
          router.push(inviteRedirect);
        } else {
          router.push('/auth/login');
        }
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
      );
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box>
        <Typography variant="h2" sx={{ mb: 4 }}>
          Email Verification
        </Typography>
        <Form
          onFinish={handleSubmit}
          sx={{ width: 400, fontSize: (theme) => theme.custom.typography.fontSize.base }}
          layout="vertical"
          autoComplete="off"
        >
          <Box sx={{ marginBottom: 3 }}>
            <Typography variant="body1">
              To complete the verification process, please click the button below:
            </Typography>
          </Box>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Accept"
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

const EmailVerification: React.FC = () => (
  <Suspense fallback={null}>
    <EmailVerificationContent />
  </Suspense>
);

export default EmailVerification;

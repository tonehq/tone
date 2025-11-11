'use client';

import { useState } from 'react';

import { Box, Stack, Typography } from '@mui/material';

import CustomButton from '@/components/shared/CustomButton';
import { Form } from '@/components/shared/FormComponent';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

export default function ForgotPasswordVerification() {
  const [loader, setLoader] = useState(false);
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get('/auth/verifyUserEmail');
      setLoader(false);
      if (res) {
        notify.success('Success', 'Email verification completed successfully', 4, 'bottomRight');
      }
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
      notify.error(
        'Verification Failed',
        errorMessage || 'Email does not exist or something went wrong',
        5,
        'bottomRight',
      );
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
}

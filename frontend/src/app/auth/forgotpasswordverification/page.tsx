'use client';

import { useState } from 'react';

import { Box, Stack } from '@mui/material';

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
}

'use client';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import { useState } from 'react';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/FormComponent';
import TextInput from '../../../components/shared/TextInput';
import { forgotPassword } from '../../../services/auth/helper';
import { useNotification } from '../../../utils/notification';
import Container from '../shared/ContainerComponent';

const ForgotPasswordPage = () => {
  const [loader, setLoader] = useState(false);
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (value['email']) {
      try {
        const res: any = await forgotPassword(value['email']);
        if (res) {
          notify.success('Email Sent', 'Password reset instructions sent to your email', 4);
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
        notify.error('Request Failed', errorMessage || 'Something went wrong', 5);
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
          If there&apos;s an account associated with this email, we will send you a link to reset
          your password.
        </Typography>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <TextInput
            name="email"
            type="email"
            label="Email"
            placeholder="Enter your email"
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
            <CustomButton
              text="Cancel"
              type="default"
              fullWidth
              onClick={() => window.history.back()}
            />
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

export default ForgotPasswordPage;

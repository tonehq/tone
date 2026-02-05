'use client';

import { Box, Checkbox, FormControlLabel, Stack, Typography, useTheme } from '@mui/material';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/FormComponent';
import TextInput from '../../../components/shared/TextInput';
import { login } from '../../../services/auth/helper';
import { useNotification } from '../../../utils/notification';
import Container from '../shared/ContainerComponent';

const LoginPage = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();
  const _redirectTo = searchParams.get('redirect') ?? '/home';

  const handleSubmit = async (values: any) => {
    setLoader(true);
    try {
      // Simulate API call
      const res: any = await login(values['email'], values['password']);

      if (res) {
        notify.success('Login Successful', 'Welcome back!', 3);
        router.push('/home');
      } else {
        notify.error('Login Failed', 'Please enter email and password', 3);
      }
    } catch (error) {
      notify.error('Login Failed', 'Please try again.', 5);
      console.log(error);
    } finally {
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box sx={{ width: '100%', maxWidth: 400 }}>
        <Typography variant="h4" sx={{ mb: 1, fontWeight: 600 }}>
          Log in to your account
        </Typography>
        <Typography variant="body1" sx={{ mb: 4, color: theme.palette.text.secondary }}>
          Welcome back! Enter your credentials to access your account
        </Typography>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <TextInput
            name="email"
            type="email"
            label="Email"
            placeholder="Enter your email"
            isRequired
          />
          <TextInput
            name="password"
            type="password"
            label="Password"
            placeholder="Enter your password"
            isRequired
          />

          <Box
            sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}
          >
            <FormControlLabel
              control={<Checkbox size="small" defaultChecked />}
              label={<Typography variant="body2">Remember me</Typography>}
            />
            <Typography
              component={Link}
              href="/auth/forgotpassword"
              sx={{
                fontSize: theme.custom.typography.fontSize.sm,
                color: theme.palette.primary.main,
                textDecoration: 'none',
                '&:hover': { textDecoration: 'underline' },
              }}
            >
              Forgot password?
            </Typography>
          </Box>

          <Stack spacing={2}>
            <CustomButton
              text="Continue"
              loading={loader}
              type="primary"
              htmlType="submit"
              fullWidth
            />
            <CustomButton
              text="Continue with Google"
              type="default"
              fullWidth
              icon={
                <img
                  src="https://developers.google.com/identity/images/g-logo.png"
                  alt="Google"
                  width={16}
                  height={16}
                />
              }
            />
          </Stack>

          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              mt: 3,
              gap: 0.5,
            }}
          >
            <Typography variant="body2">Don&apos;t have an account?</Typography>
            <Typography
              component={Link}
              href="/auth/signup"
              sx={{
                fontWeight: theme.custom.typography.fontWeight.medium,
                color: theme.palette.primary.main,
                textDecoration: 'none',
                '&:hover': { textDecoration: 'underline' },
              }}
            >
              Sign up
            </Typography>
          </Box>
        </Form>
      </Box>
    </Container>
  );
};

export default LoginPage;

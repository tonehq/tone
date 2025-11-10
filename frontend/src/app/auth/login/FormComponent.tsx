'use client';

import { useEffect, useRef, useState } from 'react';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';

import { BACKEND_URL } from '@/urls';

import { setToken } from '@/utils/auth';
import axios from '@/utils/axios';
import { auth } from '@/utils/firebase';

import Container from '../shared/ContainerComponent';

const FormComponent = (props: any) => {
  const { handleSubmit, loader } = props;
  const [isLoading, setIsLoading] = useState(true);
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const router = useRouter();
  const theme = useTheme();

  useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSignIn = async () => {
    await auth.signOut();
    const provider = new GoogleAuthProvider();
    signInWithPopup(auth, provider).then(async (result: any) => {
      const token = await result.user.getIdToken();
      try {
        const resp = await axios.get(`${BACKEND_URL}/auth/get_app_access_token_by_firebase`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        await setToken(resp.data);
        router.push('/home');
      } catch (error: any) {
        if (error?.response?.data?.detail === 'USER_NOT_FOUND') {
          router.push(
            `/auth/signup?email=${result.user.email}&name=${result.user.displayName}&firebase_uid=${
              token
            }&firebase_signup=true`,
          );
        }
      }
    });
  };

  const handleFormSubmit = (values: any) => {
    handleSubmit(values);
  };

  return (
    <Container>
      <Box>
        <Typography variant="h2" sx={{ mb: 4 }}>
          Sign in
        </Typography>
        <Form
          onFinish={handleFormSubmit}
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
          <TextInput
            name="password"
            type="password"
            label="Password"
            placeholder="Enter your password"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
          />
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Sign in"
              loading={loader}
              type="primary"
              htmlType="submit"
              sx={{ width: '100%' }}
            />
            <CustomButton
              text="Sign in with Google"
              loading={false}
              type={'default'}
              sx={{ width: '100%' }}
              onClick={handleSignIn}
              icon={
                <img
                  loading="lazy"
                  src="https://developers.google.com/identity/images/g-logo.png"
                  alt="Google"
                  width={16}
                  height={16}
                />
              }
            />
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Typography
                component={Link}
                href="/auth/forgotpassword"
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
                Forgot Password
              </Typography>
            </Box>
            <Box
              sx={{
                display: 'flex',
                fontSize: '14px',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Typography variant="body2">Don't have an account?</Typography>
              <Typography
                component={Link}
                href="/auth/signup"
                sx={{
                  fontWeight: 500,
                  color: theme.palette.primary.main,
                  ml: 0.5,
                  cursor: 'pointer',
                  textDecoration: 'none',
                  '&:hover': {
                    textDecoration: 'underline',
                  },
                }}
              >
                Sign Up
              </Typography>
            </Box>
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

export default FormComponent;

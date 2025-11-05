'use client';

import { useEffect, useRef, useState } from 'react';

import { Box, Stack } from '@mui/material';
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
      <div>
        <h2 className="mb-8">Sign in</h2>
        <Form
          onFinish={handleFormSubmit}
          className="w-[400px] text-[16px]"
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
              className="w-full"
            />
            <CustomButton
              text="Sign in with Google"
              loading={false}
              type={'default'}
              className={'w-full'}
              onClick={handleSignIn}
              icon={
                <img
                  loading="lazy"
                  src="https://developers.google.com/identity/images/g-logo.png"
                  alt="Google"
                  width={16}
                  height={16}
                  className="w-4 h-4"
                />
              }
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
                <Link href="/auth/forgotpassword" className="cursor-pointer">
                  Forgot Password
                </Link>
              </Box>
            </Box>
            <Box
              sx={{
                display: 'flex',
                fontSize: '14px',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              Don't have an account?
              <span style={{ fontWeight: 500, color: '#4058ff', marginLeft: '4px' }}>
                <Link href="/auth/signup" className="cursor-pointer">
                  Sign Up
                </Link>
              </span>
            </Box>
          </Stack>
        </Form>
      </div>
    </Container>
  );
};

export default FormComponent;

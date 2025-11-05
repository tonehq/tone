'use client';

import { useEffect, useRef, useState } from 'react';

import { Box, Stack } from '@mui/material';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';

import { signup } from '@/services/auth/helper';

import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

const SignupPage = () => {
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const params = useSearchParams();
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [loader, setLoader] = useState(false);
  const [active, setActive] = useState(0);
  const [tabs] = useState('individual');
  const { notify, contextHolder } = useNotification();

  useEffect(() => {
    const firebase_signup = params.get('firebase_signup');
    if (firebase_signup === 'true') {
      setActive(1);
    }
  }, [params]);

  useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true);

    try {
      const res: any = await signup(
        value['email'],
        value['username'],
        value['password'],
        tabs === 'individual' ? { name: value['username'] } : { name: value['org_name'] },
        params.get('firebase_uid'),
      );
      notify.success(
        'Account Created',
        'Please check your email for verification',
        4,
        'bottomRight',
      );
      if (params.get('firebase_signup') === 'true') {
        router.push('/home');
      } else {
        router.push('/auth/login');
      }
      if (res.status === 200) {
        setLoader(false);
        setActive(active + 1);
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
      notify.error('Sign Up Failed', errorMessage, 5, 'bottomRight');
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <div>
        <h2 className="mb-8">Sign Up</h2>
        <Form
          onFinish={handleSubmit}
          className="w-[400px] text-[16px]"
          layout="vertical"
          autoComplete="off"
        >
          <TextInput
            name="username"
            type="text"
            label="Username"
            placeholder="Enter Your Username"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
            defaultValue={params.get('email')?.split('@')[0] || ''}
          />
          <TextInput
            name="email"
            type="email"
            label="Email"
            placeholder="Enter Your Email"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
            defaultValue={params.get('email') || ''}
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
          <TextInput
            name="org_name"
            type="text"
            label="Organisation name"
            placeholder="Enter your organisation name"
            isRequired
            rules={[{ required: true }]}
            loading={isLoading}
          />
          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Create account"
              loading={loader}
              type="primary"
              htmlType="submit"
              className="w-full"
            />
            <CustomButton
              text="Sign in with Google"
              loading={false}
              type="default"
              className="w-full"
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
            <Box
              sx={{
                display: 'flex',
                fontSize: '14px',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              Already have an account?
              <span style={{ fontWeight: 500, color: '#4058ff', marginLeft: '4px' }}>
                <Link href="/auth/login" className="cursor-pointer">
                  Log in
                </Link>
              </span>
            </Box>
          </Stack>
        </Form>
      </div>
    </Container>
  );
};

export default SignupPage;

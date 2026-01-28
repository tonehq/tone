'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';

import { Alert, Box, Stack, Typography, useTheme } from '@mui/material';
import { debounce } from 'lodash';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';
import { TextInput } from '@/components/shared/CustomFormFields';
import { Form } from '@/components/shared/FormComponent';

import { signup } from '@/services/auth/helper';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

interface ExistingOrg {
  id: number;
  name: string;
  slug: string;
  allow_access_requests: boolean;
}

const SignupContent = () => {
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const params = useSearchParams();
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [loader, setLoader] = useState(false);
  const [active, setActive] = useState(0);
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();
  const [existingOrg, setExistingOrg] = useState<ExistingOrg | null>(null);
  const [checkingOrg, setCheckingOrg] = useState(false);

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

  const checkOrgExists = useCallback(
    debounce(async (orgName: string) => {
      if (!orgName || orgName.trim().length < 2) {
        setExistingOrg(null);
        return;
      }

      setCheckingOrg(true);
      try {
        const res = await axios.get(
          `/api/v1/auth/check_organization_exists?name=${encodeURIComponent(orgName.trim())}`,
        );
        if (res.data.exists) {
          setExistingOrg(res.data.organization);
        } else {
          setExistingOrg(null);
        }
      } catch {
        setExistingOrg(null);
      } finally {
        setCheckingOrg(false);
      }
    }, 500),
    [],
  );

  const handleOrgNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    checkOrgExists(e.target.value);
  };

  const handleSubmit = async (value: any) => {
    if (existingOrg) {
      notify.warning(
        'Organization Exists',
        'An organization with this name already exists. Please choose a different name or request access.',
        5,
        'bottomRight',
      );
      return;
    }

    setLoader(true);

    try {
      const res: any = await signup(
        value['email'],
        value['username'],
        value['password'],
        { name: value['username'] },
        params.get('firebase_uid'),
        value['org_name'],
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
        const redirect = params.get('redirect');
        if (redirect) {
          localStorage.setItem('invite_redirect', redirect);
        }
        router.push(`/auth/check-email?username=${encodeURIComponent(value['username'])}&email=${encodeURIComponent(value['email'])}`);
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
      <Box>
        <Typography variant="h2" sx={{ mb: 4 }}>
          Sign Up
        </Typography>
        <Form
          onFinish={handleSubmit}
          sx={{ width: 400, fontSize: (theme) => theme.custom.typography.fontSize.base }}
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
            label="Organisation name (optional)"
            placeholder="Enter your organisation name"
            loading={isLoading}
            onChange={handleOrgNameChange}
          />

          {existingOrg && (
            <Alert
              severity={existingOrg.allow_access_requests ? 'info' : 'warning'}
              sx={{ mt: 1, mb: 2 }}
            >
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Organization &quot;{existingOrg.name}&quot; already exists.
              </Typography>
              {existingOrg.allow_access_requests ? (
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  You can request access after signing up.
                </Typography>
              ) : (
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  Please choose a different name or contact the organization admin.
                </Typography>
              )}
            </Alert>
          )}

          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text={existingOrg ? 'Sign up & Request Access' : 'Create account'}
              loading={loader || checkingOrg}
              type="primary"
              htmlType="submit"
              sx={{ width: '100%' }}
              disabled={existingOrg ? !existingOrg.allow_access_requests : false}
            />
            <CustomButton
              text="Sign in with Google"
              loading={false}
              type="default"
              sx={{ width: '100%' }}
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
            <Box
              sx={{
                display: 'flex',
                fontSize: theme.custom.typography.fontSize.sm,
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Typography variant="body2">Already have an account?</Typography>
              <Typography
                component={Link}
                href="/auth/login"
                sx={{
                  fontWeight: theme.custom.typography.fontWeight.medium,
                  color: theme.palette.primary.main,
                  ml: 0.5,
                  cursor: 'pointer',
                  textDecoration: 'none',
                  '&:hover': {
                    textDecoration: 'underline',
                  },
                }}
              >
                Log in
              </Typography>
            </Box>
          </Stack>
        </Form>
      </Box>
    </Container>
  );
};

const SignupPage = () => (
  <Suspense fallback={null}>
    <SignupContent />
  </Suspense>
);

export default SignupPage;

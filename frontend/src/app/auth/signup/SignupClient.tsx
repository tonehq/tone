'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import { debounce } from 'lodash';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/FormComponent';
import TextInput from '../../../components/shared/TextInput';
import { signup } from '../../../services/auth/helper';
import axios from '../../../utils/axios';
import { useNotification } from '../../../utils/notification';
import Container from '../shared/ContainerComponent';

interface ExistingOrg {
  id: number;
  name: string;
  slug: string;
  allow_access_requests: boolean;
}

const SignupClient = () => {
  const [_isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const params = useSearchParams();
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [loader, setLoader] = useState(false);
  const [active, setActive] = useState(0);
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();
  const [existingOrg, setExistingOrg] = useState<ExistingOrg | null>(null);
  const [_checkingOrg, setCheckingOrg] = useState(false);

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
          `/auth/check_organization_exists?name=${encodeURIComponent(orgName.trim())}`,
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
      notify.success('Account Created', 'Please check your email for verification', 4);
      if (params.get('firebase_signup') === 'true') {
        router.push('/home');
      } else {
        const redirect = params.get('redirect');
        if (redirect) {
          localStorage.setItem('invite_redirect', redirect);
        }
        router.push(
          `/auth/check-email?username=${encodeURIComponent(value['username'])}&email=${encodeURIComponent(value['email'])}`,
        );
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
      notify.error('Sign Up Failed', errorMessage, 5);
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <Box sx={{ width: '100%', maxWidth: 400 }}>
        <Typography variant="h4" sx={{ mb: 1, fontWeight: 600 }}>
          Create your account
        </Typography>
        <Typography variant="body1" sx={{ mb: 4, color: theme.palette.text.secondary }}>
          Get started with Voice AI in minutes
        </Typography>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <TextInput
            name="username"
            type="text"
            label="Username"
            placeholder="Enter your username"
            isRequired
          />
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
            placeholder="Create a password"
            isRequired
          />
          <TextInput
            name="org_name"
            type="text"
            label="Organisation name (optional)"
            placeholder="Enter your organisation name"
            onChange={handleOrgNameChange}
          />

          <Stack spacing={2} sx={{ mt: 2 }}>
            <CustomButton
              text="Create account"
              loading={loader}
              type="primary"
              htmlType="submit"
              fullWidth
            />
            <CustomButton
              text="Sign up with Google"
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
            <Typography variant="body2">Already have an account?</Typography>
            <Typography
              component={Link}
              href="/auth/login"
              sx={{
                fontWeight: theme.custom.typography.fontWeight.medium,
                color: theme.palette.primary.main,
                textDecoration: 'none',
                '&:hover': { textDecoration: 'underline' },
              }}
            >
              Log in
            </Typography>
          </Box>
        </Form>
      </Box>
    </Container>
  );
};

export default SignupClient;

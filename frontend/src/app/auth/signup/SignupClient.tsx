'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { debounce } from 'lodash';
import { useRouter, useSearchParams } from 'next/navigation';
import { GoogleIcon } from '@/components/icons/google';
import { CustomButton, CustomLink, TextInput } from '@/components/shared';
import { type SignupFormData, signupSchema } from '@/schemas/auth';
import { signup } from '@/services/auth/helper';
import axios from '@/utils/axios';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
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
  const [existingOrg, setExistingOrg] = useState<ExistingOrg | null>(null);
  const [_checkingOrg, setCheckingOrg] = useState(false);

  const { control, handleSubmit } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: '', password: '', org_name: '' },
  });

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

  const onSubmit = async (values: SignupFormData) => {
    if (existingOrg) {
      showToast.warning(
        'Organization Exists',
        'An organization with this name already exists. Please choose a different name or request access.',
        5,
      );
      return;
    }

    setLoader(true);

    try {
      const res: any = await signup(
        values.email,
        values.password,
        {},
        params.get('firebase_uid'),
        values.org_name,
      );
      showToast.success('Account Created', 'Please check your email for verification', 4);
      if (params.get('firebase_signup') === 'true') {
        router.push('/home');
      } else {
        const redirect = params.get('redirect');
        if (redirect) {
          localStorage.setItem('invite_redirect', redirect);
        }
        router.push(`/auth/check-email?email=${encodeURIComponent(values.email)}`);
      }
      if (res.status === 200) {
        setLoader(false);
        setActive(active + 1);
      }
    } catch (error) {
      handleApiError(error);
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page">
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Create your account
        </h2>
        <p className="mb-8 text-sm text-muted-foreground">
          Get started with AI Voice Agents in minutes
        </p>

        <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
          <TextInput
            name="email"
            control={control}
            type="email"
            label="Email"
            placeholder="Enter your email"
            isRequired
          />
          <TextInput
            name="password"
            control={control}
            type="password"
            label="Password"
            placeholder="Create a password"
            isRequired
          />
          <TextInput
            name="org_name"
            control={control}
            type="text"
            label="Organisation name (optional)"
            placeholder="Enter your organisation name"
            onValueChange={(value) => checkOrgExists(value)}
          />

          <div className="space-y-3">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Create account
            </CustomButton>

            <div className="relative flex items-center">
              <div className="flex-1 border-t" />
              <span className="px-3 text-xs text-muted-foreground">or</span>
              <div className="flex-1 border-t" />
            </div>

            <CustomButton type="default" fullWidth icon={<GoogleIcon className="size-4" />}>
              Sign up with Google
            </CustomButton>
          </div>

          <div className="flex items-center justify-center gap-1">
            <span className="text-sm text-muted-foreground">Already have an account?</span>
            <CustomLink href="/auth/login">Log in</CustomLink>
          </div>
        </form>
      </div>
    </Container>
  );
};

export default SignupClient;

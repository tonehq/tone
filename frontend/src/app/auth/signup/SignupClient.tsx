'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { debounce } from 'lodash';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import CustomButton from '../../../components/shared/CustomButton';
import FormTextInput from '../../../components/shared/FormTextInput';
import { type SignupFormData, signupSchema } from '../../../schemas/auth';
import { signup } from '../../../services/auth/helper';
import axios from '../../../utils/axios';
import { handleApiError } from '../../../utils/helpers';
import { showToast } from '../../../utils/toast';
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
      <div className="w-full max-w-[400px]">
        <h4 className="mb-1 text-xl font-semibold">Create your account</h4>
        <p className="mb-4 text-[15px] text-muted-foreground">
          Get started with Voice AI in minutes
        </p>

        <form onSubmit={handleSubmit(onSubmit)} autoComplete="off" className="space-y-5">
          <FormTextInput
            name="email"
            control={control}
            type="email"
            label="Email"
            placeholder="Enter your email"
            isRequired
          />
          <FormTextInput
            name="password"
            control={control}
            type="password"
            label="Password"
            placeholder="Create a password"
            isRequired
          />
          <FormTextInput
            name="org_name"
            control={control}
            type="text"
            label="Organisation name (optional)"
            placeholder="Enter your organisation name"
            onValueChange={(value) => checkOrgExists(value)}
          />

          <div className="mt-2 flex flex-col gap-2">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Create account
            </CustomButton>
            <CustomButton
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
            >
              Sign up with Google
            </CustomButton>
          </div>

          <div className="mt-3 flex items-center justify-center gap-1">
            <span className="text-sm">Already have an account?</span>
            <Link
              href="/auth/login"
              className="font-medium text-indigo-500 no-underline hover:underline"
            >
              Log in
            </Link>
          </div>
        </form>
      </div>
    </Container>
  );
};

export default SignupClient;

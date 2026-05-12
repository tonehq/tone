'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import Container from '@/app/auth/shared/ContainerComponent';
import { GoogleIcon } from '@/components/icons/google';
import { CheckboxField, CustomButton, CustomLink, TextInput } from '@/components/shared';
import { type LoginFormData, loginSchema } from '@/schemas/auth';
import { login } from '@/services/auth/helper';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const LoginPage = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillEmail = searchParams?.get('email') ?? '';

  const { control, handleSubmit } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: prefillEmail, password: '' },
  });

  const onSubmit = async (values: LoginFormData) => {
    setLoader(true);
    try {
      const res = await login(values.email, values.password);

      if (res) {
        showToast.success('Login Successful', 'Welcome back!', 3);
        const hasOrgs = res.organizations && res.organizations.length > 0;
        const redirect = searchParams?.get('redirect');
        router.push(hasOrgs ? redirect || '/home' : '/auth/onboard');
      } else {
        showToast.error('Login Failed', 'Please enter email and password', 3);
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page">
        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">Welcome back</h2>
        <p className="mb-8 text-sm text-muted-foreground">
          Enter your credentials to access your account
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
            placeholder="Enter your password"
            isRequired
          />

          <div className="flex items-center justify-between">
            <CheckboxField id="remember" label="Remember me" defaultChecked />
            <CustomLink href="/auth/forgotpassword">Forgot password?</CustomLink>
          </div>

          <div className="space-y-3">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Continue
            </CustomButton>

            <div className="relative flex items-center">
              <div className="flex-1 border-t" />
              <span className="px-3 text-xs text-muted-foreground">or</span>
              <div className="flex-1 border-t" />
            </div>

            <CustomButton type="default" fullWidth icon={<GoogleIcon className="size-4" />}>
              Continue with Google
            </CustomButton>
          </div>

          <div className="flex items-center justify-center gap-1">
            <span className="text-sm text-muted-foreground">Don&apos;t have an account?</span>
            <CustomLink href="/auth/signup">Sign up</CustomLink>
          </div>
        </form>
      </div>
    </Container>
  );
};

export default LoginPage;

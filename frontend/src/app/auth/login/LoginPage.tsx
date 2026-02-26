'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import Container from '@/app/auth/shared/ContainerComponent';
import { GoogleIcon } from '@/components/icons/google';
import { CheckboxField, CustomButton, CustomLink, Form, TextInput } from '@/components/shared';
import { login } from '@/services/auth/helper';
import { useNotification } from '@/utils/notification';

const LoginPage = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async (values: any) => {
    setLoader(true);
    try {
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
      <div className="w-full max-w-[400px]">
        <h2 className="mb-1 text-xl font-semibold text-foreground">Log in to your account</h2>
        <p className="mb-4 text-[15px] text-muted-foreground">
          Welcome back! Enter your credentials to access your account
        </p>

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

          <div className="flex items-center justify-between">
            <CheckboxField id="remember" label="Remember me" defaultChecked />
            <CustomLink href="/auth/forgotpassword">Forgot password?</CustomLink>
          </div>

          <div className="space-y-3">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Continue
            </CustomButton>
            <CustomButton type="default" fullWidth icon={<GoogleIcon className="size-4" />}>
              Continue with Google
            </CustomButton>
          </div>
          <div className="flex items-center justify-center gap-1">
            <span className="text-sm text-foreground">Don't have an account?</span>
            <CustomLink href="/auth/signup">Sign up</CustomLink>
          </div>
        </Form>
      </div>
    </Container>
  );
};

export default LoginPage;

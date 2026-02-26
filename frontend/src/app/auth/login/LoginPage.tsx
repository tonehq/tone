'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
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
  const _redirectTo = searchParams.get('redirect') ?? '/home';

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
        <h2 className="mb-1 text-xl font-semibold text-gray-800">Log in to your account</h2>
        <p className="mb-4 text-[15px] text-gray-500">
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

          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Checkbox id="remember" defaultChecked />
              <Label htmlFor="remember" className="text-sm font-normal text-gray-800">
                Remember me
              </Label>
            </div>
            <Link
              href="/auth/forgotpassword"
              className="text-sm text-purple-500 no-underline hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <div className="flex flex-col gap-2">
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
          </div>

          <div className="mt-3 flex items-center justify-center gap-1">
            <span className="text-sm text-gray-800">Don&apos;t have an account?</span>
            <Link
              href="/auth/signup"
              className="font-medium text-purple-500 no-underline hover:underline"
            >
              Sign up
            </Link>
          </div>
        </Form>
      </div>
    </Container>
  );
};

export default LoginPage;

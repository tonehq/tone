'use client';

import { useState } from 'react';

import { useRouter } from 'next/navigation';

import { login } from '@/services/auth/helper';

import { useNotification } from '@/utils/shared/notification';

import FormComponent from './FormComponent';

const LoginPage = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async (value: any) => {
    setLoader(true);
    try {
      const res: any = await login(value['email'], value['password']);
      if (res) {
        notify.success('Login Successful', 'Welcome back!', 3, 'bottomRight');
        router.push('/home');
        setLoader(false);
      }
    } catch (error) {
      const errorMessage = 'Login failed. Please try again.';
      notify.error('Login Failed', errorMessage, 5, 'bottomRight');
      console.log(error);
      setLoader(false);
    }
  };
  return (
    <>
      {contextHolder}
      <FormComponent handleSubmit={handleSubmit} loader={loader} />
    </>
  );
};

export default LoginPage;

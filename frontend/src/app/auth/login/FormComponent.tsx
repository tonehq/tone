'use client';

import { useEffect, useRef, useState } from 'react';

import { Form, Input, Skeleton } from 'antd';
import { useForm } from 'antd/es/form/Form';
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import { BACKEND_URL } from '@/urls';

import { setToken } from '@/utils/auth';
import axios from '@/utils/axios';
import { auth } from '@/utils/firebase';

import Container from '../shared/ContainerComponent';

const FormComponent = (props: any) => {
  const { handleSubmit, loader } = props;
  const [form] = useForm();
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

  return (
    <Container>
      <div>
        <h2 className="mb-8">Sign in</h2>
        <Form
          onFinish={handleSubmit}
          className="w-[400px] text-[16px]"
          requiredMark={false}
          form={form}
          name="validateOnly"
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item name="email" label="Email" rules={[{ required: true }]}>
            {isLoading ? (
              <Skeleton.Input
                active
                style={{ width: '400px', height: '100%' }}
                className="font-[500] py-4 h-[40px] rounded-[5px]"
              />
            ) : (
              <Input placeholder={'Enter Your Email'} />
            )}
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            {isLoading ? (
              <Skeleton.Input
                active
                style={{ width: '400px', height: '100%' }}
                className="font-[500] py-4 h-[40px] rounded-[5px]"
              />
            ) : (
              <Input.Password placeholder={'Enter your passwordl'} />
            )}
          </Form.Item>
          <Form.Item>
            <ButtonComponent
              text="Sign in"
              loading={loader}
              type={'primary'}
              htmlType={'submit'}
              className={'w-full'}
              active={true}
            />
          </Form.Item>
          <Form.Item>
            <ButtonComponent
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
          </Form.Item>
          <Form.Item>
            <div className="flex justify-center items-center">
              <div className="font-[500] text-[16px] text-[#4058ff]">
                <Link href="/auth/forgotpassword" className="cursor-pointer">
                  Forgot Password
                </Link>
              </div>
            </div>
          </Form.Item>
          <Form.Item>
            <div className="flex text-[14px] justify-center items-center">
              <span>Don't have an account ?</span>
              <span className="font-[500] text-[#4058ff] ml-1">
                <Link href="/auth/signup" className="cursor-pointer">
                  Sign Up
                </Link>
              </span>
            </div>
          </Form.Item>
        </Form>
      </div>
    </Container>
  );
};

export default FormComponent;

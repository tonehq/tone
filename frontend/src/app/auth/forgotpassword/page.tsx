'use client';

import * as React from 'react';

import { Form, Input, Skeleton } from 'antd';
import { useForm } from 'antd/es/form/Form';
import Link from 'next/link';

import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

import { forgotPassword } from '@/services/auth/helper';

import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

export default function ForgotPassword() {
  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [loader, setLoader] = React.useState(false);
  const { notify, contextHolder } = useNotification();

  React.useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (value['email']) {
      try {
        const res: any = await forgotPassword(value['email']);
        if (res) {
          notify.success(
            'Email Sent',
            'Password reset instructions sent to your email',
            4,
            'bottomRight',
          );
          setLoader(false);
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
        notify.error('Request Failed', errorMessage || 'Something went wrong', 5, 'bottomRight');
        setLoader(false);
      }
    } else {
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-4">Password Reset Request</h2>
        <p className="text-gray-600 mb-6">Enter your email to reset your password.</p>
        <Form
          onFinish={handleSubmit}
          className="w-[360px] text-[16px]"
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
                style={{ width: '360px', height: '100%' }}
                className="font-[500] py-4 h-[40px] rounded-lg"
              />
            ) : (
              <Input className="py-2" placeholder={'Enter Your Email'} />
            )}
          </Form.Item>
          <Form.Item>
            <ButtonComponent
              loading={loader}
              type={'primary'}
              htmlType={'submit'}
              text="Request"
              className="w-full"
              active={true}
            />
          </Form.Item>
          <Form.Item>
            <div className="flex justify-center items-center">
              <div className="font-[500] text-[16px] text-[#4058ff]">
                <Link href="/auth/login" className="cursor-pointer">
                  Back to Login
                </Link>
              </div>
            </div>
          </Form.Item>
        </Form>
      </div>
    </Container>
  );
}

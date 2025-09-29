'use client';

import * as React from 'react';

import { Form } from 'antd';
import { useForm } from 'antd/es/form/Form';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

import ButtonComponent from '@/components/shared/UI Components/ButtonComponent';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

import Container from '../shared/ContainerComponent';

const EmailVerificationContent: React.FC = () => {
  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const params = useSearchParams();
  const [form] = useForm();
  const [loader, setLoader] = React.useState(false);
  const { notify, contextHolder } = useNotification();

  React.useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async () => {
    try {
      setLoader(true);
      await axios.get(`/auth/resend_verification_email?email=${params?.get('email')?.trim()}`);
      notify.success('Email Sent', 'Verification email resent successfully', 4, 'bottomRight');
    } catch (error) {
      setLoader(false);
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
      notify.error('Resend Failed', errorMessage || 'Something went wrong', 5, 'bottomRight');
    } finally {
      setLoader(false);
    }
  };

  return (
    <div className="flex">
      {contextHolder}
      <Container>
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
          <h2 className="mb-8">Thanks for Signing up!</h2>
          <Form
            onFinish={handleSubmit}
            className="w-[360px] text-[16px]"
            requiredMark={false}
            form={form}
            name="validateOnly"
            layout="vertical"
            autoComplete="off"
          >
            <div style={{ marginBottom: '24px' }} className="mb-6">
              <p>
                Please check your email. In a few moments, you will receive a verification email to
                confirm your account.
              </p>
            </div>
            <Form.Item>
              <ButtonComponent
                loading={loader}
                type={'primary'}
                htmlType={'submit'}
                text="Resend"
                active={true}
                className="w-full mt-2"
              />
            </Form.Item>
            <Form.Item>
              <div className="flex justify-center items-center">
                <div className="font-[500] text-[16px] text-[#4058ff]">
                  <Link href="/auth/login" className="cursor-pointer">
                    Back to Signin
                  </Link>
                </div>
              </div>
            </Form.Item>
          </Form>
        </div>
      </Container>
    </div>
  );
};

const EmailVerification: React.FC = () => (
  <React.Suspense fallback={<div>Loading...</div>}>
    <EmailVerificationContent />
  </React.Suspense>
);

export default EmailVerification;

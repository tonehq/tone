'use client';

import * as React from 'react';
import '@radix-ui/themes/styles.css';
import { useRouter, useSearchParams } from 'next/navigation';
import Container from "../shared/ContainerComponent";
import { Spinner } from "@radix-ui/themes";
import { Form } from "antd";
import { useForm } from "antd/es/form/Form";
import ButtonComponent from "@/components/auth/Shared/ButtonComponent";
import axios from '@/utils/axios';
import Link from 'next/link';

const EmailVerificationContent: React.FC = () => {
  
  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
  const params = useSearchParams();
  const [form] = useForm();
  const [loader, setLoader] = React.useState(false);
  const [toastOpen, setToastOpen] = React.useState(false);
  const [toastContent, setToastContent] = React.useState({ title: '', description: '' });

  React.useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);


  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get(`/auth/resend_verification_email?email=${params?.get('email')?.trim()}`);
      setLoader(false);
      if (res) {
        setToastContent({
          title: 'Success',
          description: 'Verification email resent successfully'
        });
        setToastOpen(true);
      }
    } catch (error) {
      setLoader(false);
      let errorMessage = '';

      if (typeof error === 'object' && error !== null && 'response' in error && 'data' in (error as any).response && 'detail' in (error as any).response.data) {
        errorMessage = (error as any).response.data.detail;
      }
      setToastContent({
        title: 'Error',
        description: errorMessage
      });
      setToastOpen(true);
    }
  };

  return (
    <div className="flex">
      <Container>
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
          <h2 className="mb-8">Thanks for Signing up!</h2>
          <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
            <div className="mb-6">
              <p>Please check your email. In a few moments, you will receive a verification email to confirm your account.</p>
            </div>
            <Form.Item>
              <ButtonComponent
                isLoading={isLoading}
                type={"primary"}
                htmlType={"submit"}
                width={"100%"}
              >
                <Spinner loading={loader} />
                Resend
              </ButtonComponent>
            </Form.Item>
            <Form.Item>
              <div className="flex justify-center items-center">
                <div className="font-[500] text-[16px] text-[#4058ff]">
                  <Link href="/auth/login" className='cursor-pointer'>
                    Back to Signin
                  </Link>
                </div>
              </div>
            </Form.Item>
          </Form>
        </div>
      </Container>
    </div>
  )
};

const EmailVerification: React.FC = () => {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <EmailVerificationContent />
    </React.Suspense>
  );
};

export default EmailVerification;

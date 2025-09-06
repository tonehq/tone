'use client'

import * as React from 'react';
import axios from '@/utils/axios';
import { useRouter, useSearchParams } from 'next/navigation';
import Container from '../shared/ContainerComponent';
import { Form } from "antd";
import { useForm } from "antd/es/form/Form";
import ButtonComponent from "@/components/Shared/UI Components/ButtonComponent";
import { useNotification } from '@/utils/shared/notification';

const EmailVerificationContent = () => {
  const [form] = useForm();
  const [loader, setLoader] = React.useState(false);
  const params = useSearchParams();
  const router = useRouter();
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get(`/auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}`);
      setLoader(false);
      if (res) {
        notify.success("Email Verified", "Your email has been verified successfully", 4, "bottomRight");
        router.push('/auth/login')
      }
    } catch (error) {
      let errorMessage = '';

      if (typeof error === 'object' && error !== null && 'response' in error && 'data' in (error as any).response && 'detail' in (error as any).response.data) {
        errorMessage = (error as any).response.data.detail;
      }
      notify.error("Verification Failed", errorMessage || "Invalid verification link", 5, "bottomRight");
      setLoader(false);
    }
  };


  return (
    <Container>
       {contextHolder}
      <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-8">Email Verification</h2>
        <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
          <div style={{ marginBottom: '24px' }} className="mb-4">
            <p>To complete the verification process, please click the button below:</p>
          </div>
          <Form.Item>
            <ButtonComponent
              loading={loader}
              type={"primary"}
              htmlType={"submit"}
              text="Accept"
              active={true}
              className="w-full"
            />
          </Form.Item>
        </Form>
      </div>
    </Container>
  );
}

const EmailVerification: React.FC = () => {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <EmailVerificationContent />
    </React.Suspense>
  );
};

export default EmailVerification;


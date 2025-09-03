'use client'

import * as React from 'react';
import { Form } from "antd";
import { useForm } from "antd/es/form/Form";
import ButtonComponent from "@/components/Shared/UI Components/ButtonComponent";
import axios from '@/utils/axios';
import Container from '../shared/ContainerComponent';

export default function ForgotPasswordVerification() {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
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
      const res = await axios.get(`/auth/verifyUserEmail`);
      setLoader(false);
      if (res) {
        setToastContent({
          title: 'Success',
          description: 'Verification email resend Sucessfully'
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
        description: 'Email does not exist  or something went wrong'
      });
      setToastOpen(true);
    }
  };


  return (
    <Container>
      <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
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
              className="w-full mt-2"
              active={true}
           />
          </Form.Item>
        </Form>
      </div>
    </Container>
  );
}


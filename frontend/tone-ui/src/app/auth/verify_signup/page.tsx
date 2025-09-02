'use client'

import * as React from 'react';
import '@radix-ui/themes/styles.css';
import axios from '@/utils/axios';
import { useRouter, useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import Container from '../shared/ContainerComponent';
import { Form} from "antd";
import { useForm } from "antd/es/form/Form";
import ButtonComponent from "@/components/auth/Shared/ButtonComponent";

const EmailVerificationContent = () => {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
  const [loader, setLoader] = React.useState(false);
  const params = useSearchParams();
  const router = useRouter();
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
      const res = await axios.get(`/auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}`);
      setLoader(false);
      if (res) {
        router.push('/auth/login')
        setToastContent({
          title: 'Success',
          description: 'Email verified sucessfully'
        });
        setToastOpen(true);
        toast.info("Email Verified Sucessfully");
      }
    } catch (error) {
      let errorMessage = '';

      if (typeof error === 'object' && error !== null && 'response' in error && 'data' in (error as any).response && 'detail' in (error as any).response.data) {
        errorMessage = (error as any).response.data.detail;
      }
      setToastContent({
        title: 'Error',
        description: errorMessage
      });
      setToastOpen(true);
      setLoader(false);
    }
  };


  return (
    <Container>
      <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-8">Email Verification</h2>
        <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
          <div className="mb-4">
            <p>To complete the verification process, please click the button below:</p>
          </div>
          <Form.Item>
            <ButtonComponent
              isLoading={isLoading}
              type={"primary"}
              htmlType={"submit"}
              width={"100%"}
            >
              Accept
            </ButtonComponent>
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


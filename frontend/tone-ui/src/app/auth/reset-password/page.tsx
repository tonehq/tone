'use client';

import * as React from 'react';
import '@radix-ui/themes/styles.css';
import { useRouter, useSearchParams } from 'next/navigation';
import logo from '../logo.png';
import Image from 'next/image';
import { useForm } from "antd/es/form/Form";
import { Form, Input, Skeleton } from "antd";
import axios from '@/utils/axios';
import Container from "../shared/ContainerComponent";
import { Spinner } from "@radix-ui/themes";
import ButtonComponent from "@/components/auth/Shared/ButtonComponent";
import ToastComponent from '@/components/toast';

const ResetPasswordContent: React.FC = () => {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
  const router = useRouter();
  const [loader, setLoader] = React.useState(false);
  const params = useSearchParams();
  const [toastOpen, setToastOpen] = React.useState(false);
  const [toastContent, setToastContent] = React.useState({ title: '', description: '' });

  React.useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true)
    if ((value["password"] && value["confirm_password"]) && (value["password"] === value["confirm_password"])) {
      try {
        const res = await axios.get(
          `/auth/acceptForgotPassword?email=${params?.get('email')}&password=${(value["password"]).trim()}&token=${params?.get('token')}`
        );
        if (res) {
          setToastContent({
            title: 'Success',
            description: 'Password updated successfully'
          });
          setToastOpen(true);
          setTimeout(() => {
            router.push('/auth/login')
          }, 2000)
        }
        setLoader(false)
      } catch (error) {
        let errorMessage = '';

        if (typeof error === 'object' && error !== null && 'response' in error && 'data' in (error as any).response && 'detail' in (error as any).response.data) {
          errorMessage = (error as any).response.data.detail;
        }
        setToastContent({
          title: 'Error',
          description: errorMessage
        });
        setLoader(false)
      }
    } else {
      setToastContent({
        title: 'Error',
        description: 'Email does not exist or something went wrong'
      });
      setToastOpen(true);
      setLoader(false)
    }
  };

  return (
    <Container>
      <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-8">Reset password</h2>
        <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[42px] rounded-lg"
              />
              :
              <Input.Password className="py-2" placeholder={"Enter your password"} />
            }
          </Form.Item>
          <Form.Item name="confirm_password" label="Confirm Password" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[42px] rounded-lg"
              />
              :
              <Input.Password className="py-2" placeholder={"Enter your confirm password"} />
            }
          </Form.Item>
          <Form.Item>
            <ButtonComponent
              isLoading={isLoading}
              type={"primary"}
              htmlType={"submit"}
              width={"100%"}
            >
              <Spinner loading={loader} />
              Update New Password
            </ButtonComponent>
          </Form.Item>
        </Form>
        <ToastComponent
          open={toastOpen}
          setOpen={setToastOpen}
          title={toastContent.title}
          description={toastContent.description}
        />
      </div>
    </Container>
  );
};

const ResetPassword: React.FC = () => {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <ResetPasswordContent />
    </React.Suspense>
  );
};

export default ResetPassword;


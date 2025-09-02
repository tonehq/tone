'use client'

import * as React from 'react';
import { useForm } from "antd/es/form/Form";
import ButtonComponent from "@/components/auth/Shared/ButtonComponent";
import { Spinner } from "@radix-ui/themes";
import { Form, Input, Skeleton } from "antd";
import Container from "../shared/ContainerComponent";
import { forgotPassword } from '@/services/auth/helper';
import Link from 'next/link';

export default function ForgotPassword() {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
  const [loader, setLoader] = React.useState(false);
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
    if (value["email"]) {
      try {
        const res: any = await forgotPassword(value["email"]);
        if (res) {
          setToastContent({
            title: 'Success',
            description: 'Verification email has been sent to your mail'
          });
          setToastOpen(true);
        }
        setLoader(false)
      } catch (error) {
        let errorMessage = '';

        if (typeof error === 'object' && error !== null && 'response' in error && 'data' in (error as any).response && 'detail' in (error as any).response.data) {
          errorMessage = (error as any).response.data.detail;
        }
        setToastContent({
          title: 'Error',
          description: 'Email does not exist or something went wrong'
        });
        setToastOpen(true);
        setLoader(false)
      }
    } else {
      setToastContent({
        title: 'Error',
        description: 'Email not exist  or something went wrong'
      });
      setToastOpen(true);
      setLoader(false)
    }
  };

  return (
    <Container>
      <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-4">Password Reset Request</h2>
        <p className="text-gray-600 mb-6">Enter your email to reset your password.</p>
        <Form onFinish={handleSubmit} className='w-[360px] text-[16px]' requiredMark={false}
          form={form}
          name="validateOnly" layout="vertical" autoComplete="off">
          <Form.Item name="email" label="Email" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[42px] rounded-lg"
              />
              :
              <Input className="py-2" placeholder={"Enter Your Email"} />
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
              Request
            </ButtonComponent>
          </Form.Item>
          <Form.Item>
            <div className="flex justify-center items-center">
              <div className="font-[500] text-[16px] text-[#4058ff]">
                <Link href="/auth/login" className='cursor-pointer'>
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

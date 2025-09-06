'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from "antd/es/form/Form";
import { Form, Input, Skeleton } from "antd";
import axios from '@/utils/axios';
import Container from "../shared/ContainerComponent";
import ButtonComponent from "@/components/Shared/UI Components/ButtonComponent";
import { useNotification } from '@/utils/shared/notification';

const ResetPasswordContent: React.FC = () => {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const router = useRouter();
  const [loader, setLoader] = React.useState(false);
  const params = useSearchParams();
  const { notify, contextHolder } = useNotification();

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
          notify.success("Password Reset", "Your password has been updated successfully", 4, "bottomRight");
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
        notify.error("Reset Failed", errorMessage || "Something went wrong", 5, "bottomRight");

        setLoader(false)
      }
    } else {
      setLoader(false)
    }
  };

  return (
    <Container>
       {contextHolder}
      <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-8">Reset password</h2>
        <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[40px] rounded-lg"
              />
              :
              <Input.Password placeholder={"Enter your password"} />
            }
          </Form.Item>
          <Form.Item name="confirm_password" label="Confirm Password" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[40px] rounded-lg"
              />
              :
              <Input.Password placeholder={"Enter your confirm password"} />
            }
          </Form.Item>
          <Form.Item>
            <ButtonComponent
              loading={loader}
              type={"primary"}
              htmlType={"submit"}
              text="Update New Password"
              active={true}
              className="w-full"
            />
          </Form.Item>
        </Form>
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


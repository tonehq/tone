"use client";

import * as React from "react";
import "@radix-ui/themes/styles.css";
import { useRouter, useSearchParams } from "next/navigation";
import { signup } from "@/services/auth/helper";
import ButtonComponent from "@/components/auth/Shared/ButtonComponent";
import ToastComponent from '@/components/toast';
import { useForm } from "antd/es/form/Form";
import { Form, Input, Skeleton } from "antd";
import { Spinner } from "@radix-ui/themes";
import Link from "next/link";
import Container from "../shared/ContainerComponent";

export default () => {
  return (
    <React.Suspense>
      <SignIn />
    </React.Suspense>
  );
};

function SignIn() {

  const [form] = useForm();

  const [isLoading, setIsLoading] = React.useState(true);
  const router = useRouter();
  const params = useSearchParams();
  const [formData, setFormData] = React.useState({
    email: "",
    password: "",
    username: "",
    confirmpassword: "",
  });

  const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
  const [loader, setLoader] = React.useState(false);
  const [active, setActive] = React.useState(0);
  const [tabs, setTabs] = React.useState("individual");

  React.useEffect(() => {
    const firebase_signup = params.get("firebase_signup");
    if (firebase_signup === "true") {
      setFormData((prevData) => ({
        ...prevData,
        email: params.get("email") || "",
      }));
      setActive(1);
    }
  }, [params]);

  const [toastOpen, setToastOpen] = React.useState(false);
  const [toastContent, setToastContent] = React.useState({
    title: "",
    description: "",
  });

  React.useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  const handleSubmit = async (value: any) => {
    setLoader(true);

    try {
      const res: any = await signup(
        value["email"],
        value["username"],
        value["password"],
        tabs === 'individual' ? { name: value["username"] } : { name: value["org_name"] },
        params.get("firebase_uid")
      );
      if (params.get("firebase_signup") === "true") {
        router.push("/editor/dashboard");
      }
      else {
        router.push("/auth/login")
      }
      if (res.status === 200) {
        setLoader(false);
        setActive(active + 1);
      }
    } catch (error) {
      let errorMessage = "";

      if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        "data" in (error as any).response &&
        "detail" in (error as any).response.data
      ) {
        errorMessage = (error as any).response.data.detail;
      }
      setToastContent({
        title: "Error",
        description: errorMessage,
      });
      setToastOpen(true);
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="max-w-md mx-auto px-6 bg-white rounded-lg shadow-md">
        <h2 className="mb-4">Sign Up</h2>
        <Form onFinish={handleSubmit} className="lg:w-[360px] max-w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
          <Form.Item name="usename" label="Username" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[42px] rounded-lg"
              />
              :
              <Input className="py-2" placeholder={"Enter Your Username"} />
            }
          </Form.Item>
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
          <Form.Item name="org_name" label="Organisation name" rules={[{ required: true }]}>
            {isLoading ?
              <Skeleton.Input
                active
                style={{ width: "360px", height: "100%" }}
                className="font-[500] py-4 h-[42px] rounded-lg"
              />
              :
              <Input className="py-2" placeholder={"Enter your organisation name"} />
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
              Create account
            </ButtonComponent>
          </Form.Item>
          <Form.Item>
            <ButtonComponent
              isLoading={isLoading}
              type={"default"}
              width={"100%"}
            >
              <span>
                <img loading="lazy" src="https://cdn.builder.io/api/v1/image/assets/TEMP/f6bb794390c33066b1b287c6fed32b735307648872bb255ad515b99fcf51d92b?apiKey=99f610f079bc4250a85747146003507a&amp;&amp;apiKey=99f610f079bc4250a85747146003507a" alt="" />
              </span>
              <span className="ml-4">Sign in with Google</span>
            </ButtonComponent>
          </Form.Item>
          <Form.Item>
            <div className="flex justify-center items-center">
              <span>Already have an account?</span>
              <span className="font-[500] text-[#4058ff] ml-1">
                <Link href={"/auth/login"} className="cursor-pointer">
                  Log in
                </Link>
              </span>
            </div>
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
}

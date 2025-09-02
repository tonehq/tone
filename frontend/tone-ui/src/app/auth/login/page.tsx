"use client";

import { useState } from "react";
// import FormComponent from "./FormComponent";
// import { login } from "@/services/auth/helper";
import { useRouter } from "next/navigation";
import { Button } from "antd";

const LoginPage = () => {
  const [loader, setLoader] = useState(false);
  const router = useRouter();

  // const handleSubmit = async (value: any) => {
  //   setLoader(true)
  //   try {
  //     const res: any = await login(value["email"], value["password"]);
  //     if (res) {
  //       router.push("/editor/dashboard");
  //       setLoader(false);
  //     }
  //   } catch (error) {
  //     console.log(error)
  //     setLoader(false);
  //   }
  // };

  return (
    <div className="flex w-full">
      Sign up
      <Button type="primary">Sign up</Button>
    </div>
  )
}

export default LoginPage;
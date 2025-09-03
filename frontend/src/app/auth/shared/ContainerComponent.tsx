import { Form } from "antd"
import Image from "next/image";
import logo from "../logo.png";
import { useForm } from "antd/es/form/Form";
import { Children, useEffect, useRef, useState } from "react";
import Testimonial from "@/components/authComponent/Testimonial";
import Logo from "@/components/authComponent/Logo";
import Footer from "@/components/authComponent/Footer";


const Container = (props: any) => {
  const { children } = props;
  
  return (
    <div className="flex h-[100vh] w-full">
      <div className="w-[50%]">
        <div className="flex flex-col justify-between">
          <div className="flex flex-col items-center justify-center rounded-lg shadow-md h-[100vh]">
            {children}
          </div>
        </div>
      </div>
      <div className="w-[50%] h-[100vh]">
        <img
            src="https://cdn.builder.io/api/v1/image/assets/TEMP/064d49d468d0952bd0a54eff0df8fb9a191373a750f515c5d402d20433ce4293?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a"
            alt="app logo"
            width={"100%"}
            style={{ objectFit: "cover", height: "99%" }}
          />
      </div>
    </div>
  )
}

export default Container;
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
  const [form] = useForm();
  const [isLoading, setIsLoading] = useState(true);
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);


  useEffect(() => {
    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(loadingTimeoutRef.current);
  }, []);

  return (
    <main className="flex flex-col justify-center bg-white h-[100vh]">
      <div className="w-full bg-white max-md:max-w-full h-full">
        <div className="flex gap-5 max-md:flex-col h-full">
          <section className="flex flex-col w-6/12 max-md:ml-0 max-md:w-full">
            <div className="flex flex-col grow max-md:max-w-full">
              <div className='h-[10%]'>
                {/* <Image src={logo} alt={"logo"} width={150} /> */}
                {/* <Logo /> */}
              </div>
              <div className='h-[80%] flex items-center justify-center'>
                {props.children}
              </div>
              {/* <div className='h-[10%]'>
                <Footer />
              </div> */}
            </div>
          </section>
          <Testimonial />
        </div>
      </div>
    </main>
  )

  // return (
  //   <div className="flex w-full">
  //     <div className="w-[50%] p-8">
  //       <div className="flex flex-col justify-between" style={{ height: "calc(100vh - 64px)" }}>
  //         <div>
  //           <Image src={logo} alt={"logo"} width={150} />
  //         </div>
  //         <div className="flex flex-col items-center rounded-lg shadow-md">
  //           {children}
  //         </div>
  //         <div className="text-[#535862]">
  //           © Clickguides
  //         </div>
  //       </div>
  //     </div>
  //     <div className="w-[50%] h-[100vh]">
  //       <Testimonial />
  //       {/* <img
  //           src="https://cdn.builder.io/api/v1/image/assets/TEMP/064d49d468d0952bd0a54eff0df8fb9a191373a750f515c5d402d20433ce4293?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a"
  //           alt="app logo"
  //           width={"100%"}
  //           height={"100%"}
  //         /> */}
  //     </div>
  //   </div>
  // )
}

export default Container;
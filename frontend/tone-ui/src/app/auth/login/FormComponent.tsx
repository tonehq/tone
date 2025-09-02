// import { Form, Input, Skeleton } from "antd";
// import { useForm } from "antd/es/form/Form";
// import ButtonComponent from "@/components/auth/Shared/ButtonComponent";
// import { useEffect, useRef, useState } from "react";
// import Container from "../shared/ContainerComponent";
// import { Spinner } from "@radix-ui/themes";
// import Link from "next/link";
// import { useSignInWithGoogle } from "react-firebase-hooks/auth";
// import { useRouter } from "next/navigation";
// import { auth } from "@/utils/firebase";
// import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
// import axios from "axios";
// import { BACKEND_URL } from "@/urls";
// import { setToken } from "@/services/auth/helper";


// const FormComponent = (props: any) => {
//     const { handleSubmit, loader } = props;
//     const [form] = useForm();
//     const [isLoading, setIsLoading] = useState(true);
//     const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
//     const [signInWithGoogle, user, loading, error] = useSignInWithGoogle(auth);
//     const router = useRouter();


//     useEffect(() => {
//         loadingTimeoutRef.current = setTimeout(() => {
//             setIsLoading(false);
//         }, 2000);

//         return () => clearTimeout(loadingTimeoutRef.current);
//     }, []);


//   const handleSignIn = async () => {
//     await auth.signOut();
//     const provider = new GoogleAuthProvider();
//     signInWithPopup(auth, provider).then(async (result) => {
//       const token = await result.user.getIdToken();
//       try {
//         const resp = await axios.get(
//           BACKEND_URL + "/auth/get_app_access_token_by_firebase",
//           {
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );
//         await setToken(resp.data);
//         router.push("/editor/dashboard")
//       } catch (error: any) {
//         if (error?.response?.data?.detail === "USER_NOT_FOUND") {
//           router.push(
//             "/auth/signup?email=" +
//               result.user.email +
//               "&name=" +
//               result.user.displayName +
//               "&firebase_uid=" +
//               token +
//               "&firebase_signup=true"
//           );
//         }
//       }
//     });
//   };


//     return(
//         <Container>
//             <div>
//             <h2 className="mb-8">Sign in</h2>
//                 <Form onFinish={handleSubmit} className="w-[360px] text-[16px]" requiredMark={false} form={form} name="validateOnly" layout="vertical" autoComplete="off">
//                     <Form.Item name="email" label="Email" rules={[{ required: true }]}>
//                        {isLoading ? 
//                             <Skeleton.Input
//                                 active
//                                 style={{ width: "360px", height:"100%"}}
//                                 className="font-[500] py-4 h-[42px] rounded-lg"
//                             />
//                          : 
//                             <Input className="py-2" placeholder={"Enter Your Email"} />
//                         }
//                     </Form.Item>
//                     <Form.Item name="password" label="Password" rules={[{ required: true }]}>
//                         {isLoading ? 
//                             <Skeleton.Input
//                                 active
//                                 style={{ width: "360px", height:"100%"}}
//                                 className="font-[500] py-4 h-[42px] rounded-lg"
//                             />
//                          : 
//                             <Input.Password className="py-2" placeholder={"Enter your passwordl"} />
//                         }
//                     </Form.Item>
//                     <Form.Item>
//                        <ButtonComponent
//                             isLoading={isLoading}
//                             type={"primary"}
//                             htmlType={"submit"}
//                             width={"100%"}
//                        >
//                         <Spinner loading={loader} />
//                             Sign in
//                        </ButtonComponent>
//                     </Form.Item>
//                     <Form.Item>
//                        <ButtonComponent
//                             isLoading={isLoading}
//                             type={"default"}
//                             width={"100%"}
//                             onClick={handleSignIn}
//                        >
//                              <span>
//                                  <img loading="lazy" src="https://cdn.builder.io/api/v1/image/assets/TEMP/f6bb794390c33066b1b287c6fed32b735307648872bb255ad515b99fcf51d92b?apiKey=99f610f079bc4250a85747146003507a&amp;&amp;apiKey=99f610f079bc4250a85747146003507a" alt="" />
//                              </span>
//                              <span className="ml-4">Sign in with Google</span>
//                        </ButtonComponent>
//                     </Form.Item>
//                     <Form.Item>
//                         <div className="flex justify-center items-center">
//                             <div className="font-[500] text-[16px] text-[#4058ff]">
//                                 <Link href="/auth/forgotpassword" className='cursor-pointer'>
//                                     Forgot Password
//                                 </Link>
//                             </div>
//                         </div>
//                     </Form.Item>
//                     <Form.Item>
//                         <div className="flex justify-center items-center">
//                             <span>Don't have an account ?</span>
//                             <span className="font-[500] text-[#4058ff] ml-1">
//                                 <Link href="/auth/signup" className='cursor-pointer'>
//                                     Sign Up
//                                 </Link>
//                             </span>
//                         </div>
//                     </Form.Item>
//                 </Form>
//             </div>
//         </Container>
//     )
// }

// export default FormComponent;
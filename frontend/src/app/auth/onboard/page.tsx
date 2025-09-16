// 'use client'

// import * as React from 'react';
// import {
//   Box,
//   Flex,
//   Heading,
//   Skeleton,
//   Callout,
//   ScrollArea,
// } from '@radix-ui/themes';
// import '@radix-ui/themes/styles.css';
// import { onBoardMenu } from '../constants';
// import { useRouter, useSearchParams } from 'next/navigation';
// import { toast } from 'sonner';
// import ToastComponent from '@/components/toast';
// import { Button } from 'antd';

// interface TabsState {
//   purpose: string[];
//   department: string[];
//   knowledge_base_tool: string[];
// }

// interface propsType {
//   setActive: React.Dispatch<React.SetStateAction<number>>;
//   email: string
// }

// function OnboardContent(props: propsType) {
//   const { setActive, email } = props;
//   const [isLoading, setIsLoading] = React.useState(true);
//   const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
//   const [currentpage, setCurrentpage] = React.useState(0);
//   const [tabs, setTabs] = React.useState<TabsState>({
//     purpose: [],
//     department: [],
//     knowledge_base_tool: []
//   });
//   const [temp, setTemp] = React.useState<string[]>([])
//   const router = useRouter();
//   const params = useSearchParams();
//   const [toastOpen, setToastOpen] = React.useState(false);
//   const [toastContent, setToastContent] = React.useState({ title: '', description: '' });

//   React.useEffect(() => {
//     loadingTimeoutRef.current = setTimeout(() => {
//       setIsLoading(false);
//     }, 2000);

//     return () => clearTimeout(loadingTimeoutRef.current);
//   }, []);

//   const handleNext = (event: React.FormEvent<HTMLFormElement>) => {
//     event.preventDefault();
//     setCurrentpage(currentpage + 1)
//   }

//   const handleBack = (event: React.FormEvent<HTMLFormElement>) => {
//     event.preventDefault();
//     if (currentpage === 0) {
//       setActive(1)
//     } else {
//       setCurrentpage(currentpage - 1)
//     }
//   }

//   const handleClick = (value: string) => {
//     if (currentpage === 0) {
//       if (tabs.purpose.includes(value)) {
//         const updatedPurpose = tabs.purpose.filter(item => item !== value);
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           purpose: updatedPurpose
//         }));
//       } else {
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           purpose: [...prevTabs.purpose, value]
//         }));
//       }
//     } else if (currentpage === 1) {
//       if (tabs.department.includes(value)) {
//         const updatedDepartment = tabs.department.filter(item => item !== value);
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           department: updatedDepartment
//         }));
//       } else {
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           department: [...prevTabs.department, value]
//         }));
//       }
//     } else if (currentpage === 2) {
//       if (tabs.knowledge_base_tool.includes(value)) {
//         const updatedKnowledgeBaseTool = tabs.knowledge_base_tool.filter(item => item !== value);
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           knowledge_base_tool: updatedKnowledgeBaseTool
//         }));
//       } else {
//         setTabs(prevTabs => ({
//           ...prevTabs,
//           knowledge_base_tool: [...prevTabs.knowledge_base_tool, value]
//         }));
//       }
//     }

//     if (temp.includes(value)) {
//       const data = temp.filter(item => item !== value)
//       setTemp(data)
//     } else {
//       setTemp((prev) => [...prev, value])
//     }
//   };

//   const handleSubmit = (event: any) => {
//     event.preventDefault();
//     setToastContent({
//       title: 'Success',
//       description: 'A verification mail has been sent to your email'
//     });
//     setToastOpen(true);
//     setTimeout(() => {
//       router.push(`/auth/emailverification?email=${(email).trim()}`)
//     }, 1000)
//   }

//   return (
//     <div>
//       <div>
//         <Box height="100%">
//           <div className="relative z-20 w-[350px] flex gap-4 items-center text-sm font-medium">
//             <Heading as="h3" size="6" mt="-1">{onBoardMenu[currentpage]?.title}</Heading>
//           </div>
//         </Box>
//         {currentpage === 1 ? <ScrollArea type="always" scrollbars="vertical" style={{ height: 400 }}>
//           <Box mb="4">
//             <Flex direction="column" justify={'center'} >
//               {onBoardMenu[currentpage]?.constent?.map((item: any, index: number) => (
//                 <Flex mt="5" justify="start" onClick={() => handleClick(item?.text)}>
//                   <Callout.Root
//                     key={index}
//                     style={{
//                       cursor: 'pointer',
//                       padding: '7px',
//                       width: '370px',
//                       ...(temp.includes(item?.text) ? { backgroundColor: '#3e63ddeb', color: 'white' } : {})
//                     }}>
//                     <Callout.Icon>
//                       <Skeleton loading={isLoading}>{item?.icon}</Skeleton>
//                     </Callout.Icon>
//                     <Callout.Text>
//                       <Skeleton loading={isLoading}>{item?.text}</Skeleton>
//                     </Callout.Text>
//                   </Callout.Root>
//                 </Flex>
//               ))}
//             </Flex>
//           </Box>
//         </ScrollArea> : ''}
//         {currentpage === 1 ? '' :
//           <Box mb="4">
//             <Flex direction="column" justify={'center'} >
//               {onBoardMenu[currentpage]?.constent?.map((item: any, index: number) => (
//                 <Flex mt="5" justify="start" onClick={() => handleClick(item?.text)}>
//                   <Callout.Root
//                     key={index}
//                     style={{
//                       cursor: 'pointer',
//                       padding: '7px',
//                       width: '370px',
//                       ...(temp.includes(item?.text) ? { backgroundColor: '#3e63ddeb', color: 'white' } : {})
//                     }}>
//                     <Callout.Icon>
//                       <Skeleton loading={isLoading}>{item?.icon}</Skeleton>
//                     </Callout.Icon>
//                     <Callout.Text>
//                       <Skeleton loading={isLoading}>{item?.text}</Skeleton>
//                     </Callout.Text>
//                   </Callout.Root>
//                 </Flex>
//               ))}
//             </Flex>
//           </Box>}

//               <Flex mt="5" justify="between" gap="3">
//                 <Skeleton loading={isLoading}>
//                   <Button  onClick={(e: any) => handleBack(e)} color="gray">
//                     Back
//                   </Button>
//                 </Skeleton>
//                 {currentpage !== 2 ?
//                 <Skeleton loading={isLoading}>
//                   <Button  onClick={(e: any) => handleNext(e)} >
//                        Next
//                   </Button>
//                 </Skeleton> : '' }
//                 {currentpage === 2 ?
//                 <Skeleton loading={isLoading}>
//                   <Button type="primary"  onClick={(e: any) => handleSubmit(e)} >
//                        Done
//                   </Button>
//                 </Skeleton> : '' }
//               </Flex>
//             </div>
//             <ToastComponent
//         open={toastOpen}
//         setOpen={setToastOpen}
//         title={toastContent.title}
//         description={toastContent.description}
//       />
//     </div>
//   );
// }

// const Onboard = (props: any) => {
//   const { setActive, email } = props;
//   return (
//     <React.Suspense fallback={<div>Loading...</div>}>
//       <OnboardContent setActive={setActive} email={email} />
//     </React.Suspense>
//   )
// }

// export default Onboard;

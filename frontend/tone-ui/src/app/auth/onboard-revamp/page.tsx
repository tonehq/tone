'use client'

import * as React from 'react';
import { onBoardMenu } from '../constants';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import ToastComponent from '@/components/toast';

interface TabsState {
    purpose: string[];
    department: string[];
    knowledge_base_tool: string[];
}

interface propsType {
    setActive: React.Dispatch<React.SetStateAction<number>>;
    email: string
}

const OnboardContent = (props: propsType) => {
    const { setActive, email } = props;
    const [isLoading, setIsLoading] = React.useState(true);
    const loadingTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>();
    const [currentpage, setCurrentpage] = React.useState(0);
    const [tabs, setTabs] = React.useState<TabsState>({
        purpose: [],
        department: [],
        knowledge_base_tool: []
    });
    const [temp, setTemp] = React.useState<string[]>([])
    const router = useRouter();
    const [toastOpen, setToastOpen] = React.useState(false);
    const [toastContent, setToastContent] = React.useState({ title: '', description: '' });

    React.useEffect(() => {
        loadingTimeoutRef.current = setTimeout(() => {
            setIsLoading(false);
        }, 2000);

        return () => clearTimeout(loadingTimeoutRef.current);
    }, []);


    const handleNext = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setCurrentpage(currentpage + 1)
    }

    const handleBack = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (currentpage === 0) {
            setActive(1)
        } else {
            setCurrentpage(currentpage - 1)
        }
    }

    const handleClick = (value: string) => {
        if (currentpage === 0) {
            if (tabs.purpose.includes(value)) {
                const updatedPurpose = tabs.purpose.filter(item => item !== value);
                setTabs(prevTabs => ({
                    ...prevTabs,
                    purpose: updatedPurpose
                }));
            } else {
                setTabs(prevTabs => ({
                    ...prevTabs,
                    purpose: [...prevTabs.purpose, value]
                }));
            }
        } else if (currentpage === 1) {
            if (tabs.department.includes(value)) {
                const updatedDepartment = tabs.department.filter(item => item !== value);
                setTabs(prevTabs => ({
                    ...prevTabs,
                    department: updatedDepartment
                }));
            } else {
                setTabs(prevTabs => ({
                    ...prevTabs,
                    department: [...prevTabs.department, value]
                }));
            }
        } else if (currentpage === 2) {
            if (tabs.knowledge_base_tool.includes(value)) {
                const updatedKnowledgeBaseTool = tabs.knowledge_base_tool.filter(item => item !== value);
                setTabs(prevTabs => ({
                    ...prevTabs,
                    knowledge_base_tool: updatedKnowledgeBaseTool
                }));
            } else {
                setTabs(prevTabs => ({
                    ...prevTabs,
                    knowledge_base_tool: [...prevTabs.knowledge_base_tool, value]
                }));
            }
        }

        if (temp.includes(value)) {
            const data = temp.filter(item => item !== value)
            setTemp(data)
        } else {
            setTemp((prev) => [...prev, value])
        }
    };

    const handleSubmit = (event: any) => {
        event.preventDefault();
        setToastContent({
            title: 'Success',
            description: 'A verification mail has been sent to your email'
        });
        setToastOpen(true);
        setTimeout(() => {
            router.push(`/auth/emailverification-revamp?email=${(email).trim()}`)
        }, 1000)
    }

    return (
        <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md w-[500px]">

            <h3 className="text-lg font-semibold mb-2">Sign Up</h3>
            <h4 className="text-md font-medium mb-4">How will you use Clickguides</h4>

            <form onSubmit={handleSubmit}>
                <div className='h-[50vh] overflow-y-auto px-6'>
                    {onBoardMenu[currentpage]?.constent.map(option => (
                        <div
                            key={option.key}
                            onClick={() => handleClick(option?.text)}
                            className={`flex items-center p-3 mb-2 rounded-md cursor-pointer transition-all duration-300 ease-in-out
                            ${temp.includes(option?.text)
                                    ? 'bg-blue-100 text-blue-700 shadow-md transform scale-105'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            <span className="mr-3 text-xl">{option.icon}</span>
                            <span>{option.text}</span>
                        </div>
                    ))}
                </div>

                <div className="flex justify-between mt-6">
                    <div
                        onClick={(e: any) => handleBack(e)}
                        className="px-4 py-2 text-sm font-medium cursor-pointer text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors duration-300"
                    >
                        Back
                    </div>
                    {currentpage !== 2 ?
                        <button
                            onClick={(e: any) => handleNext(e)}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-300"
                        >
                            Next
                        </button>
                        :
                        null
                    }
                    {currentpage === 2 ?
                        <button
                            onClick={(e: any) => handleSubmit(e)}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-300"
                        >
                            Done
                        </button>
                        :
                        null
                    }
                </div>
            </form>
            <ToastComponent
                open={toastOpen}
                setOpen={setToastOpen}
                title={toastContent.title}
                description={toastContent.description}
            />
        </div>
    );
};

export default OnboardContent;
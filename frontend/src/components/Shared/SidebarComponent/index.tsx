"use client"

import type React from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { sidemenu } from "./constant"
import { useState } from "react"
import { PanelLeft } from "lucide-react"
import Organization from "../Organization"

interface SidebarItemProps {
    icon: React.ElementType
    href: string
    active?: boolean
}

function SidebarItem({ icon: Icon, href, active }: SidebarItemProps) {
    return (
        <Link
            href={href}
            className={`flex items-center justify-center w-10 h-10 rounded-md transition-colors ${active ? "bg-[#e5e7eb] text-text" : "text-text hover:bg-[#e5e7eb] hover:text-slate-900"}`}
        >
            <Icon className="w-5 h-5" />
        </Link>
    )
}


function SidebarItemMenu({ icon: Icon, href, active, title }: any) {
    return (
        <Link
            href={href}
            className={`flex items-center w-full px-[10%] h-10 transition-colors ${active ? "bg-[#e5e7eb] text-text font-semibold" : "text-text hover:bg-[#e5e7eb] hover:text-slate-900"}`}
        >
            <div className="flex items-center justify-center gap-2">
                <Icon className="w-5 h-5" />
                <span className="text-md">{title}</span>
            </div>
        </Link>
    )
}


function Sidebar(props: any) {
    const {sidebar, setSidebar} = props;
    const pathname = usePathname();
    const [showToggleIcon, setShowToggleIcon] = useState(false);

    const isActive = (path: string) => pathname === path || pathname?.split('/')[1] === path.split('/')[1];

    return (
        <aside
            className={`flex flex-col h-screen bg-white border-r border-[#e2e8f0]
                transition-all duration-300 ease-in-out
                ${sidebar ? "w-[300px]" : "w-[60px]"}`}
            onMouseEnter={() => setShowToggleIcon(true)}
            onMouseLeave={() => setShowToggleIcon(false)}
        >
            <div style={{ height: "48px" }} className={`flex items-center border-b border-[#e2e8f0] ${!sidebar ? "justify-center" : "justify-start"}`}>
                {!sidebar ? (
                    <div className="flex items-center justify-center w-8 h-8 text-white bg-blue-700 rounded-md">
                        <span className="text-md font-semibold">T</span>
                    </div>
                ) : (
                    <div className="flex px-[10%] items-center justify-between w-full">
                        <div className="flex items-center gap-2">
                            <div style={{ width: "24px", height: "24px" }} className="flex items-center justify-center text-white bg-blue-700 rounded-md">
                                <span className="text-md font-semibold">T</span>
                            </div>
                            <div className="text-lg font-semibold text-text py-2">
                                Tone App
                            </div>
                        </div>

                        <div
                            className={`cursor-pointer hover:bg-gray-100 p-2 my-shadow rounded-md ${!sidebar ? 'opacity-100' : showToggleIcon ? 'opacity-100' : 'opacity-0'}`}
                            onClick={() => setSidebar(!sidebar)}
                        >
                            <PanelLeft color='#414651' size={20} />
                        </div>
                    </div>


                )}
            </div>
            {!sidebar ? (
                <div
                    className={`flex mt-2 justify-center cursor-pointer mx-2 my-shadow rounded-md p-1 py-2 ${!sidebar ? 'opacity-100' : 'opacity-0'}`}
                    onClick={() => setSidebar(!sidebar)}
                >
                    <PanelLeft color='#414651' size={20} />
                </div>
            ) : ""}
            <div className="m-2">
                <Organization sidebar={sidebar} />
            </div>

            {!sidebar ? (
                <div>
                    <nav className="flex flex-col items-center gap-2 py-2" >
                        {sidemenu.map((item: any, index: number) => (
                            <SidebarItem 
                                key={item.key} 
                                icon={item.icon} 
                                href={item.path} 
                                active={isActive(item.path)} 
                            />
                        ))}
                    </nav>
                </div>

            ) : (
                <nav className="flex flex-col items-center gap-2 mx-2 rounded-md" >
                    {sidemenu.map((item: any) => (
                        <SidebarItemMenu 
                            key={item.key} 
                            icon={item.icon} 
                            title={item.title} 
                            href={item.path} 
                            active={isActive(item.path)} 
                        />
                    ))}
                </nav>
            )}

            <div className="flex flex-col items-center justify-center mt-auto gap-4">
                {/* <CustomUserButton sidebar={sidebar} /> */}
            </div>
        </aside>
    )
}

export default Sidebar;

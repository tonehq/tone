import { getOrganization } from "@/services/auth/helper";
import { Avatar, Button, Card, Divider, Popover, Skeleton, Space, Spin } from "antd";
import { Building2, ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
import ButtonComponent from "../UI Components/ButtonComponent";

interface Organization {
    id: string;
    name: string;
    slug: string;
    image_url: string;
}

const Organization = (props: any) => {
    const { sidebar } = props;
    const [loader, setLoader] = useState(false)
    const [data, setData] = useState<Organization[]>([])
    const [active, setActive] = useState<Organization | null>(null);
    const [visible, setVisible] = useState(false);

    // Helper function to capitalize first letter of each word
    const startCase = (str: string) => {
        return str.replace(/\w\S*/g, (txt) => 
            txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
        );
    };

    const init = async () => {
        setLoader(true)
        try {
            const res = await getOrganization()
            if(res.data) {
                setData(res.data)
                setLoader(false)
            }
        } catch(err) {
            console.log(err)
            setLoader(false)
        }
    }

    useEffect(() => {
        init()
    }, [])

    useEffect(() => {
        if(data?.length) {
            setActive(data?.[0])
        }
    }, [data])


    const getContents = () => (
        <div style={{ width: 220 }}>
            <div style={{ marginBottom: 8, display: "block", color: "#8c8c8c" }}>
                Organization List
            </div>
            {data?.map((membership) => {
                return (
                    <div
                        key={membership.id}
                        onClick={() => setActive(membership)}
                        className={`mb-2 hover:bg-[#e5e7eb] ${
                            active?.id === membership.id ? "bg-[#e5e7eb] font-[600]" : ""
                        }`}
                        style={{
                            padding: "6px 8px",
                            borderRadius: 4,
                            cursor: "pointer",
                        }}
                    >
                        {startCase(membership.name)}
                    </div>
                );
            })}

            <Divider style={{ margin: "8px 0" }} />

            <ButtonComponent
                text="Create organization"
                onClick={() => {setVisible(false)}}
            />
        </div>
    );

    return (
        <div className="pb-2">
            {loader ?  
                <Skeleton.Button
                    active
                    shape="default"
                    style={{ width: "242px", height: "60px"}}
                    className="font-[500] py-4 h-[60px] rounded-[5px]"
                /> :
                <Popover
                    content={getContents()}
                    trigger="click"
                    open={visible}
                    onOpenChange={setVisible}
                    placement="bottomLeft"
                >
                    <Card
                        hoverable
                        style={{
                            width: sidebar ? 240 : 48,
                            borderRadius: 5,
                            cursor: "pointer",
                            border: "1px solid #e5e7eb",
                            transition: "width 0.3s ease-in-out, padding 0.3s ease-in-out",
                        }}
                        styles={{
                            body: {
                                padding: sidebar ? "4px 12px" : "8px",
                                display: "flex",
                                justifyContent: "center",
                                transition: "padding 0.3s ease-in-out",
                            }
                        }}
                    >
                        {sidebar ? (
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    width: "100%",
                                    transition: "opacity 0.3s ease-in-out",
                                    opacity: sidebar ? 1 : 0,
                                }}
                            >
                                <Space>
                                    {active?.image_url ? (
                                        <Avatar
                                            src={active?.name.charAt(0)}
                                            size={28}
                                            style={{ backgroundColor: "#f0f0f0" }}
                                        />
                                    ) : (
                                        <Building2 size={20} />
                                    )}
                                    <div style={{ transition: "opacity 0.3s ease-in-out" }}>
                                        <div className="font-semibold">
                                            {active?.name || "Select Organization"}
                                        </div>
                                        <div className="text-sm text-gray-500 mt-2">
                                            {active?.slug || "Web app"}
                                        </div>
                                    </div>
                                </Space>
                                <ChevronDown size={16} />
                            </div>
                        ) : (
                            <div style={{ transition: "opacity 0.3s ease-in-out" }}>
                                {active?.image_url ? (
                                    <Avatar
                                        src={active?.name.charAt(0)}
                                        size={28}
                                        style={{ backgroundColor: "#f0f0f0" }}
                                    />
                                ) : (
                                    <Building2 size={20} />
                                )}
                            </div>
                        )}
                    </Card>
                </Popover>
            }
        </div>
    );
};

export default Organization;
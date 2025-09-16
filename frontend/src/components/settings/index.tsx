import { fetchOrganizationList, settingsAtom } from "@/atoms/SettingsAtom";
import { getOrganization } from "@/services/auth/helper";
import { Typography } from "antd";
import { useAtom } from "jotai";
import { useEffect, useState } from "react";
import MembersTable from "./TableComponent";

const { Title } = Typography;

const Settings = () => {
    const [data] = useAtom(settingsAtom);
    const [, setData] = useAtom(fetchOrganizationList);
    const [loader, setLoader] = useState(false);

    const init = async () => {
        setLoader(true);
        try {
            const res = await getOrganization();
            if(res.data) {
                setData(res.data);
                setLoader(false);
            }
        } catch(err) {
            console.log(err);
            setLoader(false);
        }
    }


    useEffect(() => {
       init();
    }, []);

    return (
        <div>
            <Title className="mb-4" level={4}>Settings</Title>
            <MembersTable />
        </div>
    )
}

export default Settings;    

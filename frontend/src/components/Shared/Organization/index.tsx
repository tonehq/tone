import { useEffect, useState } from 'react';

import { Avatar, Card, Divider, Popover, Skeleton, Space } from 'antd';
import Cookies from 'js-cookie';
import { Building2, ChevronDown, Plus } from 'lucide-react';

import CreateOrganizationModal from '@/components/settings/ModalComponent';

import { getOrganization } from '@/services/auth/helper';

import { cn } from '@/utils/cn';
import { handleError } from '@/utils/handleError';

import ButtonComponent from '../UI Components/ButtonComponent';

interface Organization {
  id: string;
  name: string;
  slug: string;
  image_url: string;
}

const Organization = (props: any) => {
  const { isSidebarExpanded } = props;
  const [loader, setLoader] = useState(false);
  const [data, setData] = useState<Organization[]>([]);
  const [active, setActive] = useState<Organization | null>(null);
  const [visible, setVisible] = useState(false);
  const [createOrganization, setCreateOrganization] = useState(false);

  const startCase = (str: string) =>
    str.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());

  const init = async () => {
    setLoader(true);
    try {
      const res = await getOrganization();
      if (res.data) {
        setData(res.data);
        setLoader(false);
      }
    } catch (error) {
      handleError({ error });
      setLoader(false);
    }
  };

  useEffect(() => {
    init();
  }, []);

  useEffect(() => {
    if (data?.length && Cookies.get('org_tenant_id')) {
      setActive(data?.find((org) => String(org.id) === Cookies.get('org_tenant_id')) || null);
    } else if (data?.length) {
      setActive(data?.[0]);
    }
  }, [data]);

  const getContents = () => (
    <div className="w-55">
      <div className="mb-2 text-gray-500">Organization List</div>
      {data?.map((membership) => (
        <div
          key={membership.id}
          onClick={() => {
            setActive(membership);
            Cookies.set('org_tenant_id', String(membership.id));
            window.location.reload();
          }}
          className={cn(
            'mb-1 hover:bg-gray-200 px-2 py-1.5 rounded cursor-pointer',
            active?.id === membership.id && 'bg-gray-200 font-semibold',
          )}
        >
          {startCase(membership.name)}
        </div>
      ))}
      <Divider className="!my-2" />
      <ButtonComponent
        text="Create organization"
        onClick={() => setCreateOrganization(true)}
        icon={<Plus size={16} />}
      />
    </div>
  );

  return (
    <>
      {loader ? (
        <div className="mb-0">
          <Skeleton.Input active className="!w-full bg-[#636363] rounded-t-lg" />
          <Skeleton.Input active className="!w-full bg-[#636363] rounded-b-lg" />
        </div>
      ) : (
        <Popover
          content={getContents()}
          trigger="click"
          open={visible}
          onOpenChange={setVisible}
          placement="bottomLeft"
        >
          <Card
            hoverable
            className={cn(
              'cursor-pointer border border-gray-200 transition-all duration-300 rounded-md',
              isSidebarExpanded ? 'w-full' : 'w-fit !m-auto',
            )}
            styles={{
              body: {
                padding: isSidebarExpanded ? '4px 12px' : '8px',
                display: 'flex',
                justifyContent: 'center',
              },
            }}
          >
            {isSidebarExpanded ? (
              <div className="flex items-center justify-between w-full">
                <Space>
                  {active?.image_url ? (
                    <Avatar src={active?.name.charAt(0)} size={28} className="bg-gray-100" />
                  ) : (
                    <Building2 size={20} />
                  )}
                  <div>
                    <div className="font-semibold">{active?.name || 'Select Organization'}</div>
                    <div className="text-sm text-gray-500 mt-2">{active?.slug || 'Web app'}</div>
                  </div>
                </Space>
                <ChevronDown size={16} />
              </div>
            ) : (
              <div>
                {active?.image_url ? (
                  <Avatar src={active?.name.charAt(0)} size={28} className="bg-gray-100" />
                ) : (
                  <Building2 size={20} />
                )}
              </div>
            )}
          </Card>
        </Popover>
      )}
      <CreateOrganizationModal
        open={createOrganization || false}
        onCancel={() => setCreateOrganization(false)}
        onInvite={() => {}}
      />
    </>
  );
};

export default Organization;

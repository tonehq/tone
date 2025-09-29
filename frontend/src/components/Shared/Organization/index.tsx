import { useEffect, useState } from 'react';

import { Avatar, Card, Divider, Popover, Skeleton, Space } from 'antd';
import Cookies from 'js-cookie';
import { Building2, ChevronDown, Plus } from 'lucide-react';

import CreateOrganizationModal from '@/components/settings/ModalComponent';

import { getOrganization } from '@/services/auth/helper';

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
    <div style={{ width: 220 }}>
      <div style={{ marginBottom: 8, display: 'block', color: '#8c8c8c' }}>Organization List</div>
      {data?.map((membership) => (
        <div
          key={membership.id}
          onClick={() => {
            setActive(membership);
            Cookies.set('org_tenant_id', String(membership.id));
            window.location.reload();
          }}
          className={`mb-2 hover:bg-[#e5e7eb] ${
            active?.id === membership.id ? 'bg-[#e5e7eb] font-[600]' : ''
          }`}
          style={{
            padding: '6px 8px',
            borderRadius: 4,
            cursor: 'pointer',
          }}
        >
          {startCase(membership.name)}
        </div>
      ))}

      <Divider style={{ margin: '8px 0' }} />

      <ButtonComponent
        text="Create organization"
        onClick={() => {
          setCreateOrganization(true);
        }}
        icon={<Plus size={16} />}
      />
    </div>
  );

  return (
    <>
      {loader ? (
        <Skeleton.Input active className="h-[62px] !w-full bg-[#636363] rounded-lg" />
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
            style={{
              width: isSidebarExpanded ? 240 : '100%',
              borderRadius: 5,
              cursor: 'pointer',
              border: '1px solid #e5e7eb',
              transition: 'width 0.3s ease-in-out, padding 0.3s ease-in-out',
            }}
            styles={{
              body: {
                padding: isSidebarExpanded ? '4px 12px' : '8px',
                display: 'flex',
                justifyContent: 'center',
                transition: 'padding 0.3s ease-in-out',
              },
            }}
          >
            {isSidebarExpanded ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  transition: 'opacity 0.3s ease-in-out',
                  opacity: isSidebarExpanded ? 1 : 0,
                }}
              >
                <Space>
                  {active?.image_url ? (
                    <Avatar
                      src={active?.name.charAt(0)}
                      size={28}
                      style={{ backgroundColor: '#f0f0f0' }}
                    />
                  ) : (
                    <Building2 size={20} />
                  )}
                  <div style={{ transition: 'opacity 0.3s ease-in-out' }}>
                    <div className="font-semibold">{active?.name || 'Select Organization'}</div>
                    <div className="text-sm text-gray-500 mt-2">{active?.slug || 'Web app'}</div>
                  </div>
                </Space>
                <ChevronDown size={16} />
              </div>
            ) : (
              <div style={{ transition: 'opacity 0.3s ease-in-out' }}>
                {active?.image_url ? (
                  <Avatar
                    src={active?.name.charAt(0)}
                    size={28}
                    style={{ backgroundColor: '#f0f0f0' }}
                  />
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

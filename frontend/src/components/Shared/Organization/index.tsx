import { useEffect, useState } from 'react';

import { Avatar, Card, CardContent, Divider, Popover, Skeleton, Stack } from '@mui/material';
import Cookies from 'js-cookie';
import { Building2, ChevronDown, Plus } from 'lucide-react';

import CreateOrganizationModal from '@/components/settings/ModalComponent';

import { getOrganization } from '@/services/auth/helper';

import { cn } from '@/utils/cn';
import { handleError } from '@/utils/handleError';

import CustomButton from '../CustomButton';

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
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

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

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
    setVisible(true);
  };

  const handleClose = () => {
    setAnchorEl(null);
    setVisible(false);
  };

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
      <Divider sx={{ my: 2 }} />
      <CustomButton
        text="Create organization"
        onClick={() => setCreateOrganization(true)}
        icon={<Plus size={16} />}
      />
    </div>
  );

  return (
    <>
      {loader ? (
        <Skeleton
          variant="rectangular"
          height={63}
          sx={{ width: '100%', bgcolor: '#636363', borderRadius: '8px' }}
        />
      ) : (
        <>
          <Popover
            open={visible}
            anchorEl={anchorEl}
            onClose={handleClose}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'left',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'left',
            }}
          >
            {getContents()}
          </Popover>
          <Card
            onClick={handleClick}
            sx={{
              cursor: 'pointer',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              transition: 'all 0.3s',
              '&:hover': {
                boxShadow: 2,
              },
              width: isSidebarExpanded ? '100%' : 'fit-content',
              margin: '0 auto',
            }}
          >
            <CardContent
              sx={{
                padding: isSidebarExpanded ? '4px 12px' : '8px',
                display: 'flex',
                justifyContent: 'center',
                '&:last-child': {
                  paddingBottom: isSidebarExpanded ? '4px' : '8px',
                },
              }}
            >
              {isSidebarExpanded ? (
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  width="100%"
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    {active?.image_url ? (
                      <Avatar sx={{ width: 28, height: 28, bgcolor: '#f3f4f6' }}>
                        {active?.name.charAt(0)}
                      </Avatar>
                    ) : (
                      <Building2 size={20} />
                    )}
                    <div>
                      <div className="font-semibold">{active?.name || 'Select Organization'}</div>
                      <div className="text-sm text-gray-500 mt-2">{active?.slug || 'Web app'}</div>
                    </div>
                  </Stack>
                  <ChevronDown size={16} />
                </Stack>
              ) : (
                <div>
                  {active?.image_url ? (
                    <Avatar sx={{ width: 28, height: 28, bgcolor: '#f3f4f6' }}>
                      {active?.name.charAt(0)}
                    </Avatar>
                  ) : (
                    <Building2 size={20} />
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </>
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

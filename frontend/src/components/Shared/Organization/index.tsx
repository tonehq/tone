import { useEffect, useState } from 'react';

import {
  Avatar,
  Box,
  Card,
  CardContent,
  Divider,
  Popover,
  Skeleton,
  Stack,
  Typography,
  useTheme,
} from '@mui/material';
import Cookies from 'js-cookie';
import { Building2, ChevronDown, Plus } from 'lucide-react';

import CreateOrganizationModal from '@/components/settings/ModalComponent';

import { getOrganization } from '@/services/auth/helper';

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

  const theme = useTheme();
  const getContents = () => (
    <Box sx={{ width: 220 }}>
      <Typography variant="body2" sx={{ mb: 2, color: theme.palette.text.secondary }}>
        Organization List
      </Typography>
      {data?.map((membership) => (
        <Box
          key={membership.id}
          onClick={() => {
            setActive(membership);
            Cookies.set('org_tenant_id', String(membership.id));
            window.location.reload();
          }}
          sx={{
            mb: 1,
            px: 2,
            py: 1.5,
            borderRadius: theme.custom.borderRadius.base,
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: theme.palette.grey[200],
            },
            ...(active?.id === membership.id && {
              backgroundColor: theme.palette.grey[200],
              fontWeight: theme.custom.typography.fontWeight.semibold,
            }),
          }}
        >
          {startCase(membership.name)}
        </Box>
      ))}
      <Divider sx={{ my: 2 }} />
      <CustomButton
        text="Create organization"
        onClick={() => setCreateOrganization(true)}
        icon={<Plus size={16} />}
      />
    </Box>
  );

  return (
    <>
      {loader ? (
        <Skeleton
          variant="rectangular"
          height={63}
          sx={{ width: '100%', bgcolor: '#636363', borderRadius: theme.custom.borderRadius.base }}
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
              borderRadius: theme.custom.borderRadius.base,
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
                    <Box>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: theme.custom.typography.fontWeight.semibold }}
                      >
                        {active?.name || 'Select Organization'}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{ color: theme.palette.text.secondary, mt: 0.5, display: 'block' }}
                      >
                        {active?.slug || 'Web app'}
                      </Typography>
                    </Box>
                  </Stack>
                  <ChevronDown size={16} />
                </Stack>
              ) : (
                <Box>
                  {active?.image_url ? (
                    <Avatar sx={{ width: 28, height: 28, bgcolor: '#f3f4f6' }}>
                      {active?.name.charAt(0)}
                    </Avatar>
                  ) : (
                    <Building2 size={20} />
                  )}
                </Box>
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

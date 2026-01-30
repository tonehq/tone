import { Box } from '@mui/material';
import { Home } from 'lucide-react';

import ContentSection from './ContentSection';

interface BreadcrumbItem {
  title: React.ReactNode;
  href?: string;
  className?: string;
}

const Settings = () => {
  const breadcrumbItems: BreadcrumbItem[] = [
    {
      title: <Home size={14} />,
      href: '/home',
    },
    { title: 'Settings' },
  ];

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <ContentSection />
    </Box>
  );
};

export default Settings;

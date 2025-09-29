import { BreadcrumbProps } from 'antd';
import { Home } from 'lucide-react';

import PageHeader from '@/components/Shared/PageHeader';

import ContentSection from './ContentSection';

const Settings = () => {
  const breadcrumbItems: BreadcrumbProps['items'] = [
    {
      title: <Home size={14} />,
      href: '/home',
      className: '!flex items-center justify-center mt-[1px]',
    },
    { title: 'Settings' },
  ];

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" breadcrumbItems={breadcrumbItems} showNotifications={false} />
      <ContentSection />
    </div>
  );
};

export default Settings;

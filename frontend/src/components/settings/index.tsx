import { Home } from 'lucide-react';

import PageHeader from '@/components/shared/PageHeader';

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
      className: '!flex items-center justify-center mt-[1px]',
    },
    { title: 'Settings' },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Settings" breadcrumbItems={breadcrumbItems} showNotifications={false} />
      <ContentSection />
    </div>
  );
};

export default Settings;

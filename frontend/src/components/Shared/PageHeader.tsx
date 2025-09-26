import React from 'react';

import { HomeOutlined } from '@ant-design/icons';
import { Breadcrumb, Typography } from 'antd';
import Link from 'next/link';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  breadcrumbItems?: BreadcrumbItem[];
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, breadcrumbItems = [] }) => {
  const items = [
    { title: <HomeOutlined />, href: '/' },
    ...breadcrumbItems.map((item) => ({
      title: item.href ? <Link href={item.href}>{item.label}</Link> : item.label,
    })),
  ];

  return (
    <div className="w-full bg-[#f3f5f9] px-6 py-4">
      <Typography.Title level={2} style={{ marginTop: 8, marginBottom: 0 }}>
        {title}
      </Typography.Title>
      {breadcrumbItems.length > 0 && <Breadcrumb items={items} />}
    </div>
  );
};

export default PageHeader;

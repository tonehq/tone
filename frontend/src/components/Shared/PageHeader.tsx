import React, { memo } from 'react';

import { BreadcrumbProps, Typography } from 'antd';

import CustomBreadCrumb from '@/components/Shared/CustomBreadCrumb';

interface PageHeaderProps {
  title: string;
  breadcrumbItems?: BreadcrumbProps['items'];
  breadcrumbItemRender?: BreadcrumbProps['itemRender'];
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  breadcrumbItems = [],
  breadcrumbItemRender,
}) => (
  <div className="w-full bg-[#f3f5f9] py-2">
    <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 4 }}>
      {title}
    </Typography.Title>
    {breadcrumbItems.length > 0 && (
      <CustomBreadCrumb items={breadcrumbItems} itemRender={breadcrumbItemRender} />
    )}
  </div>
);

export default memo(PageHeader);

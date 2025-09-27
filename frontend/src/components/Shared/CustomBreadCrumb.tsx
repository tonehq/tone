import { FC, memo } from 'react';

import { Breadcrumb, BreadcrumbProps } from 'antd';
import Link from 'next/link';

import { cn } from '@/utils/cn';

interface CustomBreadCrumbProps {
  items: BreadcrumbProps['items'];
  itemRender?: BreadcrumbProps['itemRender'];
}

const CustomBreadCrumb: FC<CustomBreadCrumbProps> = ({ items, itemRender }) => (
  <Breadcrumb
    items={items}
    itemRender={
      itemRender
        ? itemRender
        : (route) => {
            if (route.href) {
              return (
                <Link href={route.href} className={cn('text-sm', route.className)}>
                  {route.title}
                </Link>
              );
            }
            return <span className={cn('text-sm', route.className)}>{route.title}</span>;
          }
    }
  />
);

export default memo(CustomBreadCrumb);

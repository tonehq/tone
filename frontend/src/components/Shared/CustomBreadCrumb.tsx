import { FC, memo } from 'react';

import { Breadcrumbs, Typography } from '@mui/material';
import Link from 'next/link';

import { cn } from '@/utils/cn';

interface BreadcrumbItem {
  title: React.ReactNode;
  href?: string;
  className?: string;
}

interface CustomBreadCrumbProps {
  items: BreadcrumbItem[];
  itemRender?: (item: BreadcrumbItem, index: number, items: BreadcrumbItem[]) => React.ReactNode;
}

const CustomBreadCrumb: FC<CustomBreadCrumbProps> = ({ items, itemRender }) => {
  const defaultItemRender = (item: BreadcrumbItem, index: number, allItems: BreadcrumbItem[]) => {
    const isLast = index === allItems.length - 1;

    if (item.href && !isLast) {
      return (
        <Link
          href={item.href}
          className={cn('text-sm no-underline hover:underline', item.className)}
          style={{ color: 'inherit' }}
        >
          {item.title}
        </Link>
      );
    }

    return (
      <Typography
        className={cn('text-sm', item.className)}
        sx={{
          color: isLast ? 'text.primary' : 'text.secondary',
        }}
      >
        {item.title}
      </Typography>
    );
  };

  return (
    <Breadcrumbs
      separator="/"
      sx={{
        '& .MuiBreadcrumbs-separator': {
          margin: '0 4px',
        },
      }}
    >
      {items.map((item, index) => (
        <span key={index}>
          {itemRender ? itemRender(item, index, items) : defaultItemRender(item, index, items)}
        </span>
      ))}
    </Breadcrumbs>
  );
};

export default memo(CustomBreadCrumb);

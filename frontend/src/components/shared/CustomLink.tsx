'use client';

import { cn } from '@/lib/utils';
import Link from 'next/link';
import React from 'react';

interface CustomLinkProps extends React.ComponentProps<typeof Link> {
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

const CustomLink = React.forwardRef<HTMLAnchorElement, CustomLinkProps>(
  ({ children, icon, fullWidth = false, className, ...props }, ref) => (
    <Link
      ref={ref}
      className={cn(
        'text-sm font-medium text-primary underline-offset-2 hover:underline cursor-pointer',
        fullWidth && 'w-full',
        className,
      )}
      {...props}
    >
      {icon && <span className="mr-2 inline-flex shrink-0">{icon}</span>}
      {children}
    </Link>
  ),
);

CustomLink.displayName = 'CustomLink';

export default CustomLink;

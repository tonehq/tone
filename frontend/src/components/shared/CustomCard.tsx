'use client';

import React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

export interface CustomCardProps {
  title?: React.ReactNode;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  headerClassName?: string;
  centered?: boolean;
}

export default function CustomCard({
  title,
  description,
  icon,
  action,
  children,
  footer,
  className,
  contentClassName,
  headerClassName,
  centered = false,
}: CustomCardProps) {
  const hasHeader = title || icon || action;

  return (
    <Card className={className}>
      {hasHeader && (
        <CardHeader className={cn(centered && 'text-center', headerClassName)}>
          {action ? (
            <div className="flex items-center justify-between">
              <div className={cn(centered && 'text-center')}>
                {icon && <div className="mb-2">{icon}</div>}
                {title && <CardTitle className="text-xl">{title}</CardTitle>}
                {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
              </div>
              {action}
            </div>
          ) : (
            <>
              {icon && <div className={cn('mb-2', centered && 'mx-auto')}>{icon}</div>}
              {title && <CardTitle className="text-xl">{title}</CardTitle>}
              {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
            </>
          )}
        </CardHeader>
      )}
      {children && <CardContent className={contentClassName}>{children}</CardContent>}
      {footer && <div className="px-6 pb-6 pt-0">{footer}</div>}
    </Card>
  );
}

'use client';

import React from 'react';

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import type { CustomDrawerProps } from '@/types/components';
import { cn } from '@/utils/cn';

export type { CustomDrawerProps } from '@/types/components';

const CustomDrawer: React.FC<CustomDrawerProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  side = 'right',
  width,
  className,
  contentClassName,
  showCloseButton = true,
}) => (
  <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
    <SheetContent
      side={side}
      showCloseButton={showCloseButton}
      className={cn('flex flex-col gap-0 p-0', width, className)}
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      {title && (
        <SheetHeader className="shrink-0 px-6 pt-6 pb-4">
          <SheetTitle>{title}</SheetTitle>
          {description && <SheetDescription>{description}</SheetDescription>}
        </SheetHeader>
      )}

      {children && (
        <div className={cn('min-h-0 flex-1 overflow-y-auto px-6 pb-6', contentClassName)}>
          {children}
        </div>
      )}

      {footer && <div className="shrink-0 border-t bg-muted/30 px-6 py-4">{footer}</div>}
    </SheetContent>
  </Sheet>
);

export default CustomDrawer;

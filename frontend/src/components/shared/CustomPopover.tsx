'use client';

import React from 'react';

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { CustomPopoverProps } from '@/types/components';
import { cn } from '@/utils/cn';

export type { CustomPopoverProps } from '@/types/components';

const CustomPopover: React.FC<CustomPopoverProps> = ({
  open,
  onOpenChange,
  trigger,
  title,
  children,
  footer,
  align = 'end',
  side,
  sideOffset = 6,
  width = 'w-60',
  className,
  contentClassName,
  contentProps,
}) => (
  <Popover open={open} onOpenChange={onOpenChange}>
    <PopoverTrigger asChild>{trigger}</PopoverTrigger>
    <PopoverContent
      align={align}
      side={side}
      sideOffset={sideOffset}
      className={cn('p-0', width, className)}
      {...contentProps}
    >
      {title && (
        <div className="border-b border-border px-3 py-2">
          {typeof title === 'string' ? (
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {title}
            </p>
          ) : (
            title
          )}
        </div>
      )}

      {children && (
        <div className={cn('max-h-72 overflow-y-auto p-2', contentClassName)}>{children}</div>
      )}

      {footer && (
        <div className="flex items-center justify-between gap-2 border-t border-border p-2">
          {footer}
        </div>
      )}
    </PopoverContent>
  </Popover>
);

export default CustomPopover;

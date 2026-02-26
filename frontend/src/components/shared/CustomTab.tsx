'use client';

import { cn } from '@/utils/cn';
import { Tabs as TabsPrimitive } from 'radix-ui';
import React from 'react';

export interface TabItem {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
  children: React.ReactNode;
}

interface CustomTabProps {
  items: TabItem[];
  defaultActiveKey?: string;
  activeKey?: string;
  onTabChange?: (key: string) => void;
  className?: string;
  tabBarClassName?: string;
  contentClassName?: string;
}

const CustomTab: React.FC<CustomTabProps> = ({
  items,
  defaultActiveKey,
  activeKey,
  onTabChange,
  className,
  tabBarClassName,
  contentClassName,
}) => {
  const defaultKey = defaultActiveKey ?? items[0]?.key;

  return (
    <TabsPrimitive.Root
      defaultValue={activeKey ? undefined : defaultKey}
      value={activeKey}
      onValueChange={onTabChange}
      className={cn('flex flex-col', className)}
    >
      <TabsPrimitive.List
        className={cn(
          'inline-flex w-full items-center gap-0 border-b border-border',
          tabBarClassName,
        )}
      >
        {items.map((item) => (
          <TabsPrimitive.Trigger
            key={item.key}
            value={item.key}
            disabled={item.disabled}
            className={cn(
              'relative inline-flex cursor-pointer items-center gap-1.5 border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors',
              'hover:text-foreground',
              'data-[state=active]:border-primary data-[state=active]:text-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2',
              'disabled:pointer-events-none disabled:opacity-50',
              "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
            )}
          >
            {item.icon}
            {item.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>

      {items.map((item) => (
        <TabsPrimitive.Content
          key={item.key}
          value={item.key}
          className={cn('flex-1 outline-none', contentClassName)}
        >
          {item.children}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
};

export default CustomTab;

import React, { useState } from 'react';

import { Badge } from 'antd';

import { TabItem } from '@/types/tab';

import { cn } from '@/utils/cn';

interface CustomTabProps {
  items: TabItem[];
  defaultActiveKey?: string;
  activeKey?: string;
  onChange?: (key: string) => void;
  variant?: 'default' | 'pills' | 'underline' | 'cards';
  size?: 'small' | 'medium' | 'large';
  centered?: boolean;
  className?: string;
  animated?: boolean;
}

const CustomTab: React.FC<CustomTabProps> = ({
  items,
  defaultActiveKey,
  activeKey: controlledActiveKey,
  onChange,
  variant = 'default',
  size = 'medium',
  centered = false,
  className = '',
  animated = true,
}) => {
  const [internalActiveKey, setInternalActiveKey] = useState(
    defaultActiveKey || items[0]?.key || '',
  );

  const activeKey = controlledActiveKey !== undefined ? controlledActiveKey : internalActiveKey;

  const handleTabClick = (key: string, disabled?: boolean) => {
    if (disabled) return;

    if (controlledActiveKey === undefined) {
      setInternalActiveKey(key);
    }
    onChange?.(key);
  };

  const getTabClasses = (item: TabItem, isActive: boolean) => {
    const baseClasses =
      'relative cursor-pointer transition-all duration-300 flex items-center gap-2';
    const sizeClasses = {
      small: 'px-3 py-1.5 text-sm',
      medium: 'px-4 py-2 text-base',
      large: 'px-6 py-3 text-lg',
    };

    const variantClasses = {
      default: isActive
        ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
        : 'text-gray-600 hover:text-blue-500 hover:bg-gray-50',
      pills: isActive
        ? 'text-white bg-blue-600 rounded-full shadow-lg'
        : 'text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-full',
      underline: isActive
        ? 'text-blue-600 border-b-2 border-blue-600'
        : 'text-gray-600 hover:text-blue-500 border-b-2 border-transparent',
      cards: isActive
        ? 'text-blue-600 bg-white rounded-t-lg border border-gray-200 border-b-white -mb-px shadow-sm'
        : 'text-gray-600 hover:text-blue-500 hover:bg-gray-50 rounded-t-lg border border-transparent',
    };

    return cn(
      baseClasses,
      sizeClasses[size],
      variantClasses[variant],
      item.disabled && 'opacity-50 cursor-not-allowed hover:bg-transparent hover:text-gray-600',
    );
  };

  const getContainerClasses = () => {
    const baseClasses = 'flex relative';
    const centeredClasses = centered ? 'justify-center' : 'justify-start';
    const variantContainerClasses = {
      default: 'border-b border-gray-200',
      pills: 'bg-gray-100 rounded-full p-1',
      underline: 'border-b border-gray-200',
      cards: 'border-b border-gray-200',
    };

    return cn(baseClasses, centeredClasses, variantContainerClasses[variant], className);
  };

  const activeItem = items.find((item) => item.key === activeKey);

  return (
    <div className="w-full">
      <div className={getContainerClasses()}>
        {items.map((item) => {
          const isActive = item.key === activeKey;

          return (
            <div
              key={item.key}
              className={getTabClasses(item, isActive)}
              onClick={() => handleTabClick(item.key, item.disabled)}
              role="tab"
              aria-selected={isActive}
              aria-disabled={item.disabled}
            >
              {item.icon && (
                <span
                  className={cn(isActive ? 'text-current' : 'text-gray-400', 'transition-colors')}
                >
                  {item.icon}
                </span>
              )}

              <span className="font-medium">{item.label}</span>

              {item.badge && (
                <Badge
                  count={item.badge}
                  size="small"
                  className={cn(
                    'ml-1',
                    isActive
                      ? '[&_.ant-badge-count]:bg-white [&_.ant-badge-count]:text-blue-600'
                      : '[&_.ant-badge-count]:bg-blue-600 [&_.ant-badge-count]:text-white',
                  )}
                />
              )}

              {animated && isActive && variant === 'underline' && (
                <div
                  className={cn(
                    'absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full transition-all duration-300 ease-out scale-x-100 origin-left',
                  )}
                />
              )}

              {animated && isActive && variant === 'pills' && (
                <div
                  className={cn(
                    'absolute inset-0 bg-blue-600 rounded-full -z-10 transition-all duration-300 ease-out scale-100 opacity-100',
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {activeItem?.content && (
        <div key={activeKey} className={cn('mt-4', animated && 'animate-fade-in')}>
          {activeItem.content}
        </div>
      )}
    </div>
  );
};

export default CustomTab;

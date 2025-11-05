import React, { useState } from 'react';

import { Badge, Tabs, Tab, Box } from '@mui/material';

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

  const handleTabChange = (_: React.SyntheticEvent, newValue: string) => {
    if (controlledActiveKey === undefined) {
      setInternalActiveKey(newValue);
    }
    onChange?.(newValue);
  };

  const activeItem = items.find((item) => item.key === activeKey);

  // Use MUI Tabs for underline variant, custom for others
  if (variant === 'underline') {
    return (
      <div className="w-full">
        <Tabs
          value={activeKey}
          onChange={handleTabChange}
          centered={centered}
          className={className}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 500,
              minHeight: size === 'small' ? 40 : size === 'large' ? 56 : 48,
              fontSize: size === 'small' ? 14 : size === 'large' ? 16 : 15,
            },
          }}
        >
          {items.map((item) => (
            <Tab
              key={item.key}
              value={item.key}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {item.icon && <span>{item.icon}</span>}
                  <span>{item.label}</span>
                  {item.badge && (
                    <Badge
                      badgeContent={item.badge}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          fontSize: '10px',
                          height: '16px',
                          minWidth: '16px',
                        },
                      }}
                    />
                  )}
                </Box>
              }
              disabled={item.disabled}
            />
          ))}
        </Tabs>
        {activeItem?.content && (
          <Box
            key={activeKey}
            sx={{ mt: 2, ...(animated && { animation: 'fadeIn 0.3s ease-out' }) }}
          >
            {activeItem.content}
          </Box>
        )}
      </div>
    );
  }

  // Custom implementation for other variants
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
      cards: isActive
        ? 'text-blue-600 bg-white rounded-t-lg border border-gray-200 border-b-white -mb-px shadow-sm'
        : 'text-gray-600 hover:text-blue-500 hover:bg-gray-50 rounded-t-lg border border-transparent',
      underline: isActive
        ? 'text-blue-600 border-b-2 border-blue-600'
        : 'text-gray-600 hover:text-blue-500 border-b-2 border-transparent',
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
                  badgeContent={item.badge}
                  color="primary"
                  sx={{
                    '& .MuiBadge-badge': {
                      fontSize: '10px',
                      height: '16px',
                      minWidth: '16px',
                    },
                  }}
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

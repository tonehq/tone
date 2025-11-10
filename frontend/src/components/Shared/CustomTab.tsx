import React, { useState } from 'react';

import { alpha, Badge, Box, SxProps, Tab, Tabs, Theme, useTheme } from '@mui/material';

import { TabItem } from '@/types/tab';

interface CustomTabProps {
  items: TabItem[];
  defaultActiveKey?: string;
  activeKey?: string;
  onChange?: (key: string) => void;
  variant?: 'default' | 'pills' | 'underline' | 'cards';
  size?: 'small' | 'medium' | 'large';
  centered?: boolean;
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

  const theme = useTheme();
  // Use MUI Tabs for underline variant, custom for others
  if (variant === 'underline') {
    return (
      <Box sx={{ width: '100%' }}>
        <Tabs
          value={activeKey}
          onChange={handleTabChange}
          centered={centered}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: theme.custom.typography.fontWeight.medium,
              minHeight: size === 'small' ? 40 : size === 'large' ? 56 : 48,
              fontSize:
                size === 'small'
                  ? theme.custom.typography.fontSize.sm
                  : size === 'large'
                    ? theme.custom.typography.fontSize.base
                    : theme.custom.typography.fontSize.sm,
            },
          }}
        >
          {items.map((item) => (
            <Tab
              key={item.key}
              value={item.key}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {item.icon && <Box component="span">{item.icon}</Box>}
                  <Box component="span">{item.label}</Box>
                  {item.badge && (
                    <Badge
                      badgeContent={item.badge}
                      color="primary"
                      sx={{
                        '& .MuiBadge-badge': {
                          fontSize: theme.custom.typography.fontSize.xs,
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
      </Box>
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

  const getTabSx = (item: TabItem, isActive: boolean): SxProps<Theme> => {
    const sizeStyles: Record<string, SxProps<Theme>> = {
      small: { px: 1.5, py: 0.75, fontSize: theme.custom.typography.fontSize.sm },
      medium: { px: 2, py: 1, fontSize: theme.custom.typography.fontSize.base },
      large: { px: 3, py: 1.5, fontSize: theme.custom.typography.fontSize.lg },
    };

    const variantStyles: Record<string, SxProps<Theme>> = {
      default: isActive
        ? {
            color: theme.palette.primary.main,
            borderBottom: `2px solid ${theme.palette.primary.main}`,
            backgroundColor: alpha(theme.palette.primary.main, 0.05),
          }
        : {
            color: theme.palette.text.secondary,
            '&:hover': {
              color: theme.palette.primary.main,
              backgroundColor: theme.palette.grey[50],
            },
          },
      pills: isActive
        ? {
            color: theme.palette.common.white,
            backgroundColor: theme.palette.primary.main,
            borderRadius: '9999px',
            boxShadow: 2,
          }
        : {
            color: theme.palette.text.secondary,
            borderRadius: '9999px',
            '&:hover': {
              color: theme.palette.primary.main,
              backgroundColor: alpha(theme.palette.primary.main, 0.05),
            },
          },
      cards: isActive
        ? {
            color: theme.palette.primary.main,
            backgroundColor: theme.palette.background.default,
            borderTopLeftRadius: 8,
            borderTopRightRadius: 8,
            border: `1px solid ${theme.palette.divider}`,
            borderBottom: `1px solid ${theme.palette.background.default}`,
            marginBottom: '-1px',
            boxShadow: 1,
          }
        : {
            color: theme.palette.text.secondary,
            borderTopLeftRadius: 8,
            borderTopRightRadius: 8,
            border: '1px solid transparent',
            '&:hover': {
              color: theme.palette.primary.main,
              backgroundColor: theme.palette.grey[50],
            },
          },
      underline: isActive
        ? {
            color: theme.palette.primary.main,
            borderBottom: `2px solid ${theme.palette.primary.main}`,
          }
        : {
            color: theme.palette.text.secondary,
            borderBottom: '2px solid transparent',
            '&:hover': {
              color: theme.palette.primary.main,
            },
          },
    };

    return {
      position: 'relative',
      cursor: item.disabled ? 'not-allowed' : 'pointer',
      transition: 'all 0.3s',
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      ...sizeStyles[size],
      ...variantStyles[variant],
      ...(item.disabled && {
        opacity: 0.5,
        '&:hover': {
          backgroundColor: 'transparent',
          color: theme.palette.text.secondary,
        },
      }),
    } as SxProps<Theme>;
  };

  const getContainerSx = () => {
    const variantContainerStyles = {
      default: { borderBottom: `1px solid ${theme.palette.divider}` },
      pills: { backgroundColor: theme.palette.grey[100], borderRadius: '9999px', p: 0.5 },
      underline: { borderBottom: `1px solid ${theme.palette.divider}` },
      cards: { borderBottom: `1px solid ${theme.palette.divider}` },
    };

    return {
      display: 'flex',
      position: 'relative',
      justifyContent: centered ? 'center' : 'flex-start',
      ...variantContainerStyles[variant],
    };
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={getContainerSx()}>
        {items.map((item) => {
          const isActive = item.key === activeKey;

          return (
            <Box
              key={item.key}
              sx={getTabSx(item, isActive)}
              onClick={() => handleTabClick(item.key, item.disabled)}
              role="tab"
              aria-selected={isActive}
              aria-disabled={item.disabled}
            >
              {item.icon && (
                <Box
                  component="span"
                  sx={{
                    color: isActive ? 'currentColor' : theme.palette.text.disabled,
                    transition: 'color 0.3s',
                  }}
                >
                  {item.icon}
                </Box>
              )}

              <Box component="span" sx={{ fontWeight: theme.custom.typography.fontWeight.medium }}>
                {item.label}
              </Box>

              {item.badge && (
                <Badge
                  badgeContent={item.badge}
                  color="primary"
                  sx={{
                    '& .MuiBadge-badge': {
                      fontSize: theme.custom.typography.fontSize.xs,
                      height: '16px',
                      minWidth: '16px',
                    },
                  }}
                />
              )}
            </Box>
          );
        })}
      </Box>

      {activeItem?.content && (
        <Box
          key={activeKey}
          sx={{
            mt: 2,
            ...(animated && { animation: 'fadeIn 0.3s ease-out' }),
          }}
        >
          {activeItem.content}
        </Box>
      )}
    </Box>
  );
};

export default CustomTab;

'use client';

import React, { useState } from 'react';

import { Menu, MenuItem, MenuProps as MuiMenuProps, useTheme } from '@mui/material';

interface MenuItemType {
  key: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

interface CustomDropdownProps extends Omit<MuiMenuProps, 'open' | 'onClose' | 'anchorEl'> {
  items: MenuItemType[];
  children: React.ReactNode;
  trigger?: ('click' | 'hover' | 'contextMenu')[];
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  items,
  children,
  trigger = ['click'],
  ...rest
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    if (trigger.includes('click')) {
      setAnchorEl(event.currentTarget);
    }
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleMenuItemClick = (item: MenuItemType) => {
    if (item.onClick) {
      item.onClick();
    }
    handleClose();
  };

  return (
    <>
      <div onClick={handleClick} style={{ display: 'inline-block', cursor: 'pointer' }}>
        {children}
      </div>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        slotProps={{
          paper: {
            sx: {
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
              mt: 1,
            },
          },
        }}
        {...rest}
      >
        {items.map((item) => (
          <MenuItem
            key={item.key}
            onClick={() => handleMenuItemClick(item)}
            disabled={item.disabled}
            sx={{
              padding: '8px 16px',
              fontSize: '14px',
              '&:hover': {
                backgroundColor: '#f9fafb',
              },
              ...(item.danger && {
                color: theme.palette.error.main,
                '&:hover': {
                  backgroundColor: theme.palette.error.light,
                },
              }),
            }}
          >
            {item.icon && <span style={{ marginRight: 8 }}>{item.icon}</span>}
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default CustomDropdown;

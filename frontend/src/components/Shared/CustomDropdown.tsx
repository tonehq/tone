'use client';

import React from 'react';

import type { MenuProps } from 'antd';
import { Dropdown, type DropdownProps } from 'antd';

interface CustomDropdownProps extends Omit<DropdownProps, 'menu' | 'getPopupContainer'> {
  items: MenuProps['items'];
  children: React.ReactNode;
  trigger?: ('click' | 'hover' | 'contextMenu')[];
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  items,
  children,
  trigger = ['click'],
  ...rest
}) => (
  <Dropdown menu={{ items }} trigger={trigger} getPopupContainer={() => document.body} {...rest}>
    {children}
  </Dropdown>
);

export default CustomDropdown;

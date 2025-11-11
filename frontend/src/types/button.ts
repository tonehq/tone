import React from 'react';

import { ButtonProps as MuiButtonProps, SxProps, Theme } from '@mui/material';
import { LucideIcon } from 'lucide-react';

export interface ButtonProps {
  icon?: LucideIcon | React.ReactNode;
  text?: string;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
  className?: string;
  sx?: SxProps<Theme>;
  loading?: boolean;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  htmlType?: MuiButtonProps['type'];
}

'use client';

import React from 'react';

import { Button, CircularProgress, SxProps, Theme, useTheme } from '@mui/material';

interface CustomButtonProps {
  text: string;

  loading?: boolean;

  type?: 'primary' | 'default' | 'text' | 'link' | 'danger';

  htmlType?: 'button' | 'submit' | 'reset';

  onClick?: () => void;

  disabled?: boolean;

  icon?: React.ReactNode;

  sx?: SxProps<Theme>;

  fullWidth?: boolean;
}

const CustomButton: React.FC<CustomButtonProps> = ({
  text,

  loading = false,

  type = 'default',

  htmlType = 'button',

  onClick,

  disabled = false,

  icon,

  sx,

  fullWidth = false,
}) => {
  const theme = useTheme();

  const getVariant = () => {
    if (type === 'primary' || type === 'danger') return 'contained';

    if (type === 'text' || type === 'link') return 'text';

    return 'outlined';
  };

  const getColor = () => {
    if (type === 'danger') return 'error';

    if (type === 'primary') return 'primary';

    return 'inherit';
  };

  const getStyles = (): SxProps<Theme> => {
    const baseStyles: SxProps<Theme> = {
      textTransform: 'none',

      fontWeight: theme.custom.typography.fontWeight.medium,

      fontSize: theme.custom.typography.fontSize.base,

      borderRadius: theme.custom.borderRadius.base,

      height: 42,

      ...(fullWidth && { width: '100%' }),
    };

    if (type === 'primary') {
      return {
        ...baseStyles,

        backgroundColor: theme.palette.primary.main,

        '&:hover': {
          backgroundColor: theme.palette.primary.dark,
        },
      };
    }

    if (type === 'default') {
      return {
        ...baseStyles,

        borderColor: '#e2e8f0',

        color: theme.palette.text.primary,

        '&:hover': {
          borderColor: '#d1d5db',

          backgroundColor: '#f9fafb',
        },
      };
    }

    return baseStyles;
  };

  return (
    <Button
      variant={getVariant()}
      color={getColor()}
      type={htmlType}
      onClick={onClick}
      disabled={disabled || loading}
      startIcon={loading ? <CircularProgress size={18} color="inherit" /> : icon}
      sx={{ ...getStyles(), ...(sx ?? {}) } as SxProps<Theme>}
    >
      {loading ? 'Loading...' : text}
    </Button>
  );
};

export default CustomButton;

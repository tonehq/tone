'use client';

import React from 'react';

import { Button, CircularProgress, ButtonProps as MuiButtonProps, useTheme } from '@mui/material';
import { ChevronRight } from 'lucide-react';

import { ButtonProps } from '@/types/button';

// Button style constants - moved from constants file
const BUTTON_STYLES = {
  height: '36px',
  borderRadius: '5px',
  fontWeight: 500,
  fontSize: '16px',
  defaultClassName:
    'border-slate-200 !outline-none !ring-0 !shadow-none h-9 bg-white text-sm text-slate-700 hover:bg-slate-50',
} as const;

const CustomButton: React.FC<ButtonProps> = ({
  icon: Icon,
  text,
  onClick,
  type = 'default',
  disabled,
  className,
  loading,
  htmlType,
}) => {
  const theme = useTheme();

  // Map Ant Design types to MUI variants
  const getVariant = () => {
    if (type === 'primary') return 'contained';
    if (type === 'text' || type === 'link') return 'text';
    return 'outlined';
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || loading) {
      e.preventDefault();
      return;
    }
    onClick?.(e);
  };

  const buttonColors = theme.custom.button;

  // Get button styles based on type (Ant Design style)
  const getButtonStyles = () => {
    switch (type) {
      case 'primary':
        return {
          backgroundColor: buttonColors.active.backgroundColor,
          color: buttonColors.active.color,
          '&:hover': {
            backgroundColor: buttonColors.active.hover.backgroundColor,
          },
          '&:disabled': {
            backgroundColor: buttonColors.active.disabled.backgroundColor,
            color: buttonColors.active.disabled.color,
            opacity: buttonColors.active.disabled.opacity,
          },
        };
      case 'dashed':
        return {
          backgroundColor: buttonColors.inactive.backgroundColor,
          color: buttonColors.inactive.color,
          borderColor: buttonColors.inactive.borderColor,
          borderStyle: 'dashed',
          '&:hover': {
            borderColor: buttonColors.inactive.borderColor,
            backgroundColor: buttonColors.inactive.backgroundColor,
          },
          '&:disabled': {
            backgroundColor: buttonColors.inactive.disabled.backgroundColor,
            color: buttonColors.inactive.disabled.color,
            opacity: buttonColors.inactive.disabled.opacity,
          },
        };
      case 'link':
      case 'text':
        return {
          backgroundColor: 'transparent',
          color: buttonColors.active.backgroundColor,
          border: 'none',
          boxShadow: 'none',
          '&:hover': {
            backgroundColor: 'transparent',
            color: buttonColors.active.hover.backgroundColor,
          },
          '&:disabled': {
            color: buttonColors.inactive.disabled.color,
            opacity: buttonColors.inactive.disabled.opacity,
          },
        };
      default: // 'default'
        return {
          backgroundColor: buttonColors.inactive.backgroundColor,
          color: buttonColors.inactive.color,
          borderColor: buttonColors.inactive.borderColor,
          '&:hover': {
            borderColor: buttonColors.inactive.borderColor,
            backgroundColor: buttonColors.inactive.backgroundColor,
          },
          '&:disabled': {
            backgroundColor: buttonColors.inactive.disabled.backgroundColor,
            color: buttonColors.inactive.disabled.color,
            opacity: buttonColors.inactive.disabled.opacity,
          },
        };
    }
  };

  // Get spinner color based on type
  const getSpinnerColor = () => {
    if (type === 'primary') {
      return theme.custom.button.spinner.active;
    }
    if (type === 'link' || type === 'text') {
      return buttonColors.active.backgroundColor;
    }
    return theme.custom.button.spinner.inactive;
  };

  const buttonProps: MuiButtonProps = {
    variant: getVariant(),
    onClick: handleClick,
    disabled: disabled || loading,
    type: htmlType || 'button',
    className: `${BUTTON_STYLES.defaultClassName} ${className || ''}`,
    sx: {
      height: BUTTON_STYLES.height,
      borderRadius: BUTTON_STYLES.borderRadius,
      fontWeight: BUTTON_STYLES.fontWeight,
      textAlign: 'center',
      textTransform: 'none',
      position: 'relative',
      ...getButtonStyles(),
    },
  };

  const renderIcon = () => {
    if (!Icon) return null;
    if (Icon === ChevronRight) {
      return <Icon className="w-4 h-4 font-semibold" />;
    }
    if (typeof Icon === 'function') {
      return <Icon className="w-4 h-4 font-semibold" />;
    }
    return <span className="w-4 h-4 font-semibold">{Icon}</span>;
  };

  const renderContent = () => {
    if (loading) {
      return (
        <>
          <CircularProgress
            size={16}
            thickness={4}
            sx={{
              color: getSpinnerColor(),
              marginRight: text ? '8px' : 0,
            }}
          />
          {text}
        </>
      );
    }

    return text;
  };

  // Determine icon position
  const iconPosition = Icon === ChevronRight ? 'endIcon' : 'startIcon';
  const iconToShow = loading ? undefined : renderIcon();

  return (
    <Button {...buttonProps} {...(iconToShow && { [iconPosition]: iconToShow })}>
      {renderContent()}
    </Button>
  );
};

export default CustomButton;

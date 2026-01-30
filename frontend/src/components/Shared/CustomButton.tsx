'use client';

import React from 'react';

import { Button, CircularProgress, ButtonProps as MuiButtonProps, useTheme } from '@mui/material';
import { ChevronRight } from 'lucide-react';

import { ButtonProps } from '@/types/button';

// Button style constants - moved from constants file
// Note: fontWeight and fontSize are now dynamically retrieved from theme in the component

const CustomButton: React.FC<ButtonProps> = ({
  icon: Icon,
  text,
  onClick,
  type = 'default',
  disabled,
  className,
  sx,
  loading,
  htmlType,
}) => {
  const theme = useTheme();

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
    className: className,
    sx: {
      width: '100%',
      height: '36px',
      borderRadius: '5px',
      fontWeight: theme.custom.typography.fontWeight.medium,
      fontSize: theme.custom.typography.fontSize.base,
      textAlign: 'center',
      textTransform: 'none',
      position: 'relative',
      outline: 'none',
      boxShadow: 'none',
      ...getButtonStyles(),
      ...sx,
    },
  };

  const renderIcon = () => {
    if (!Icon) return null;
    if (Icon === ChevronRight) {
      return <Icon size={16} style={{ fontWeight: theme.custom.typography.fontWeight.semibold }} />;
    }
    if (typeof Icon === 'function') {
      return <Icon size={16} style={{ fontWeight: theme.custom.typography.fontWeight.semibold }} />;
    }
    return Icon;
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

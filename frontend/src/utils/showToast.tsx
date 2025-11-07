'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { Box, IconButton, Snackbar, Typography } from '@mui/material';
import { AlertTriangle, CheckCircle, Info, X, XCircle } from 'lucide-react';

export type ToastStatus = 'success' | 'error' | 'info' | 'warning';
export type ToastVariant = 'notification' | 'message';

interface ToastContextType {
  showToast: (config: ShowToastConfig) => void;
}

interface ShowToastConfig {
  status: ToastStatus;
  message: string;
  description?: string;
  duration?: number;
  placement?: 'topRight' | 'topLeft' | 'top' | 'bottomRight' | 'bottomLeft' | 'bottom';
  variant?: ToastVariant;
  style?: React.CSSProperties;
}

const ToastContext = createContext<ToastContextType | null>(null);

interface ToastState {
  open: boolean;
  message: string;
  description?: string;
  status: ToastStatus;
  duration: number;
  vertical: 'top' | 'bottom';
  horizontal: 'left' | 'center' | 'right';
}

// Legacy global context for backward compatibility
let toastContext: ToastContextType | null = null;

// Icon mapping for Ant Design style
const getIcon = (status: ToastStatus, iconColor: string) => {
  const iconProps = { size: 16 };
  switch (status) {
    case 'success':
      return <CheckCircle {...iconProps} color={iconColor} />;
    case 'error':
      return <XCircle {...iconProps} color={iconColor} />;
    case 'warning':
      return <AlertTriangle {...iconProps} color={iconColor} />;
    case 'info':
    default:
      return <Info {...iconProps} color={iconColor} />;
  }
};

// Color mapping for Ant Design style borders and backgrounds
const getColors = (status: ToastStatus) => {
  switch (status) {
    case 'success':
      return {
        borderLeft: '#52c41a',
        iconBg: '#f6ffed',
        iconColor: '#52c41a',
      };
    case 'error':
      return {
        borderLeft: '#ff4d4f',
        iconBg: '#fff2f0',
        iconColor: '#ff4d4f',
      };
    case 'warning':
      return {
        borderLeft: '#faad14',
        iconBg: '#fffbe6',
        iconColor: '#faad14',
      };
    case 'info':
    default:
      return {
        borderLeft: '#1890ff',
        iconBg: '#e6f7ff',
        iconColor: '#1890ff',
      };
  }
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toastState, setToastState] = useState<ToastState>({
    open: false,
    message: '',
    status: 'info',
    duration: 3000,
    vertical: 'top',
    horizontal: 'right',
  });

  const showToast = useCallback((config: ShowToastConfig) => {
    const { status, message, description, duration = 3000, placement = 'topRight' } = config;

    const [vertical, horizontal] = placement.split(/(?=[A-Z])/) as [
      'top' | 'bottom',
      'left' | 'center' | 'right',
    ];

    setToastState({
      open: true,
      message,
      description,
      status,
      duration: duration * 1000,
      vertical,
      horizontal: horizontal || 'right',
    });
  }, []);

  const handleClose = useCallback(() => {
    setToastState((prev) => ({ ...prev, open: false }));
  }, []);

  // Set global context for legacy showToast function
  useEffect(() => {
    toastContext = { showToast };
  }, [showToast]);

  const colors = getColors(toastState.status);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <Snackbar
        open={toastState.open}
        autoHideDuration={toastState.duration}
        onClose={handleClose}
        anchorOrigin={{ vertical: toastState.vertical, horizontal: toastState.horizontal }}
        sx={{
          '& .MuiSnackbar-root': {
            top: '24px !important',
            bottom: '24px !important',
          },
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            boxShadow:
              '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
            borderLeft: `4px solid ${colors.borderLeft}`,
            padding: '16px 24px',
            minWidth: '384px',
            maxWidth: '384px',
            position: 'relative',
            '&:hover': {
              boxShadow:
                '0 6px 16px 0 rgba(0, 0, 0, 0.12), 0 3px 6px -4px rgba(0, 0, 0, 0.16), 0 9px 28px 8px rgba(0, 0, 0, 0.09)',
            },
          }}
        >
          {/* Icon */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: colors.iconBg,
              marginRight: '16px',
              flexShrink: 0,
              marginTop: toastState.description ? '2px' : '0',
            }}
          >
            {getIcon(toastState.status, colors.iconColor)}
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              sx={{
                fontSize: '16px',
                fontWeight: 500,
                lineHeight: '24px',
                color: 'rgba(0, 0, 0, 0.85)',
                marginBottom: toastState.description ? '4px' : 0,
              }}
            >
              {toastState.message}
            </Typography>
            {toastState.description && (
              <Typography
                sx={{
                  fontSize: '14px',
                  lineHeight: '22px',
                  color: 'rgba(0, 0, 0, 0.65)',
                  marginTop: '4px',
                }}
              >
                {toastState.description}
              </Typography>
            )}
          </Box>

          {/* Close Button */}
          <IconButton
            onClick={handleClose}
            sx={{
              padding: '4px',
              marginLeft: '12px',
              color: 'rgba(0, 0, 0, 0.45)',
              '&:hover': {
                color: 'rgba(0, 0, 0, 0.75)',
                backgroundColor: 'rgba(0, 0, 0, 0.04)',
              },
              flexShrink: 0,
            }}
          >
            <X size={14} />
          </IconButton>
        </Box>
      </Snackbar>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

// Legacy function for backward compatibility
export function initToast() {
  // This is now handled by ToastProvider
  return null;
}

export function showToast(config: ShowToastConfig) {
  if (toastContext) {
    toastContext.showToast(config);
  }
}

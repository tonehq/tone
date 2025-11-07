'use client';

import React, { ReactNode } from 'react';

import { Box, Dialog, DialogActions, DialogContent, DialogTitle, IconButton } from '@mui/material';
import { X } from 'lucide-react';

import CustomButton from './CustomButton';

export interface ModalAction {
  key: string;
  text: string;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
}

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string | ReactNode;
  children: ReactNode;
  actions?: ModalAction[];
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
  fullWidth?: boolean;
  contentPadding?: number;
  actionsPadding?: number;
  actionsGap?: number;
  borderRadius?: string;
  hideActions?: boolean;
  titleClassName?: string;
  contentClassName?: string;
  hideCloseIcon?: boolean;
  isFooterExpanded?: boolean;
  footerClassName?: string;
}

const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  children,
  actions = [],
  maxWidth = 'sm',
  fullWidth = true,
  contentPadding = 2,
  actionsPadding = 2,
  actionsGap = 1,
  borderRadius = '5px',
  hideActions = false,
  titleClassName,
  contentClassName,
  hideCloseIcon = false,
  isFooterExpanded = false,
  footerClassName,
}) => (
  <Dialog
    open={open}
    onClose={onClose}
    maxWidth={maxWidth}
    fullWidth={fullWidth}
    PaperProps={{
      sx: {
        borderRadius,
      },
    }}
  >
    {title && (
      <DialogTitle
        className={titleClassName}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingRight: 2,
        }}
      >
        <Box component="span">{title}</Box>
        {!hideCloseIcon && (
          <IconButton
            onClick={onClose}
            size="small"
            sx={{
              padding: '4px',
              color: 'text.secondary',
              '&:hover': {
                backgroundColor: 'rgba(0, 0, 0, 0.04)',
              },
            }}
          >
            <X size={20} />
          </IconButton>
        )}
      </DialogTitle>
    )}
    <DialogContent className={contentClassName}>
      <Box sx={{ mt: contentPadding > 0 ? contentPadding : 0 }}>{children}</Box>
    </DialogContent>
    {!hideActions && actions.length > 0 && (
      <DialogActions
        sx={{
          padding: actionsPadding,
          gap: actionsGap,
          flexDirection: isFooterExpanded ? 'column' : 'row',
        }}
        className={footerClassName}
      >
        {actions.map((action) => (
          <CustomButton
            key={action.key}
            text={action.text}
            type={action.type || 'default'}
            onClick={action.onClick}
            loading={action.loading}
            disabled={action.disabled}
            className={isFooterExpanded ? 'w-full' : ''}
          />
        ))}
      </DialogActions>
    )}
  </Dialog>
);

export default Modal;

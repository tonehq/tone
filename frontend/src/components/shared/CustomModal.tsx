'use client';

import { CustomButton } from '@/components/shared';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { CustomModalProps } from '@/types/components';
import { cn } from '@/utils/cn';
import { X } from 'lucide-react';
import React from 'react';

export type { CustomModalProps } from '@/types/components';

const CustomModal: React.FC<CustomModalProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  onCancel,
  confirmLoading = false,
  confirmType = 'primary',
  confirmDisabled = false,
  hideFooter = false,
  width,
  className,
  contentClassName,
  showCloseButton = true,
}) => {
  const handleCancel = () => {
    (onCancel ?? onClose)();
  };

  const showFooter = !hideFooter && footer !== null;
  const hasDefaultFooter = showFooter && footer === undefined;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        // Cap the modal to the viewport and lay it out as header / scrollable body / footer
        // so a tall form (e.g. a searchable timezone select) never overflows off-screen —
        // the body scrolls internally while the header + footer stay pinned.
        className={cn(
          'flex max-h-[calc(100dvh-2rem)] flex-col gap-0 p-0',
          width ?? 'sm:max-w-lg',
          className,
        )}
        showCloseButton={false}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        {title && (
          <DialogHeader className="shrink-0 px-6 pt-4 pb-2">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-lg font-semibold">{title}</DialogTitle>
              {showCloseButton && (
                <DialogClose className="cursor-pointer rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-0 focus:ring-offset-0">
                  <X className="size-4" />
                  <span className="sr-only">Close</span>
                </DialogClose>
              )}
            </div>
            {description && (
              <DialogDescription className="mt-1.5 text-sm leading-relaxed">
                {description}
              </DialogDescription>
            )}
          </DialogHeader>
        )}

        {children && (
          <div
            className={cn(
              'min-h-0 min-w-0 flex-1 overflow-y-auto py-4 pl-6 pr-6',
              contentClassName,
            )}
          >
            {children}
          </div>
        )}

        {showFooter && (
          <DialogFooter className="shrink-0 bg-muted/30 px-6 py-4">
            {hasDefaultFooter ? (
              <>
                <CustomButton type="default" onClick={handleCancel} disabled={confirmLoading}>
                  {cancelText}
                </CustomButton>
                <CustomButton
                  type={confirmType}
                  onClick={onConfirm}
                  loading={confirmLoading}
                  disabled={confirmDisabled}
                >
                  {confirmText}
                </CustomButton>
              </>
            ) : (
              footer
            )}
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default CustomModal;

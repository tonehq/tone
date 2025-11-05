import { showToast } from '../showToast';

export const useNotification = () => {
  const notify = {
    success: (
      message: string,
      description?: string,
      duration?: number,
      placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight',
    ) => {
      showToast({
        status: 'success',
        message,
        description,
        duration: duration || 4,
        placement: placement || 'topRight',
        variant: 'notification',
      });
    },
    error: (
      message: string,
      description?: string,
      duration?: number,
      placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight',
    ) => {
      showToast({
        status: 'error',
        message,
        description,
        duration: duration || 4,
        placement: placement || 'topRight',
        variant: 'notification',
      });
    },
    info: (
      message: string,
      description?: string,
      duration?: number,
      placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight',
    ) => {
      showToast({
        status: 'info',
        message,
        description,
        duration: duration || 4,
        placement: placement || 'topRight',
        variant: 'notification',
      });
    },
    warning: (
      message: string,
      description?: string,
      duration?: number,
      placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight',
    ) => {
      showToast({
        status: 'warning',
        message,
        description,
        duration: duration || 4,
        placement: placement || 'topRight',
        variant: 'notification',
      });
    },
  };

  return { notify, contextHolder: null };
};

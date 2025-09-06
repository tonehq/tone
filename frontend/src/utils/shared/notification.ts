import { notification } from 'antd';

export const useNotification = () => {
  const [api, contextHolder] = notification.useNotification();

  const notify = {
    success: (message: string, description?: string, duration?: number, placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight') => {
      api.success({ 
        message, 
        description, 
        duration: duration || 4,
        placement: placement || 'topRight'
      });
    },
    error: (message: string, description?: string, duration?: number, placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight') => {
      api.error({ 
        message, 
        description, 
        duration: duration || 4,
        placement: placement || 'topRight'
      });
    },
    info: (message: string, description?: string, duration?: number, placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight') => {
      api.info({ 
        message, 
        description, 
        duration: duration || 4,
        placement: placement || 'topRight'
      });
    },
    warning: (message: string, description?: string, duration?: number, placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight') => {
      api.warning({ 
        message, 
        description, 
        duration: duration || 4,
        placement: placement || 'topRight'
      });
    },
  };

  return { notify, contextHolder };
};
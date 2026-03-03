import { toast } from 'sonner';

export const showToast = {
  success: (title: string, description?: string, duration?: number) =>
    toast.success(title, { description, duration: duration ? duration * 1000 : 3000 }),

  error: (title: string, description?: string, duration?: number) =>
    toast.error(title, { description, duration: duration ? duration * 1000 : 5000 }),

  warning: (title: string, description?: string, duration?: number) =>
    toast.warning(title, { description, duration: duration ? duration * 1000 : 4000 }),

  info: (title: string, description?: string, duration?: number) =>
    toast.info(title, { description, duration: duration ? duration * 1000 : 3000 }),
};

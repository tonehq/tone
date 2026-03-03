import { toast } from 'sonner';

/**
 * Function-based toast notifications powered by Sonner.
 * Can be called from any file — components, helpers, services, etc.
 *
 * Usage:
 *   showToast.success('Login Successful', 'Welcome back!');
 *   showToast.error('Error', 'Something went wrong');
 */
export const showToast = {
  success: (title: string, message: string, duration?: number) =>
    toast.success(title, { description: message, duration: duration ? duration * 1000 : 3000 }),

  error: (title: string, message: string, duration?: number) =>
    toast.error(title, { description: message, duration: duration ? duration * 1000 : 5000 }),

  warning: (title: string, message: string, duration?: number) =>
    toast.warning(title, { description: message, duration: duration ? duration * 1000 : 4000 }),

  info: (title: string, message: string, duration?: number) =>
    toast.info(title, { description: message, duration: duration ? duration * 1000 : 3000 }),
};

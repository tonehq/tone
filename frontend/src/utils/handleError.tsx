import { showToast } from './showToast';

export interface HandleErrorOptions {
  error: any;
  defaultError?: string;
}

export function handleError({ error, defaultError }: HandleErrorOptions) {
  // 401: Unauthorized
  if (error?.status === 401 || error?.status === 403) {
    showToast({
      status: 'error',
      message: 'Unauthorized',
      description: error?.response?.data?.detail || 'Your session has expired. Please login again.'
    });
    setTimeout(() => {
      localStorage.clear();
      if (typeof document !== 'undefined') {
        const cookiesArr = document.cookie.split(';');
        for (const cookie of cookiesArr) {
          const eqPos = cookie.indexOf('=');
          const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
          document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
        }
      }
      window.location.href = '/auth/login';
    }, 1000);
    return;
  }

  // Network error
  if (error?.code === 'ERR_NETWORK') {
    showToast({
      status: 'error',
      message: 'Network Error',
      description: 'A network error occurred. Please check your connection.'
    });
    return;
  }

  // Backend error response
  if (error?.response?.data) {
    const errors = error.response.data;
    // Handle FastAPI style: { detail: 'Message' }
    if (typeof errors === 'object' && typeof errors.detail === 'string') {
      showToast({
        status: 'error',
        message: 'Error',
        description: errors.detail
      });
      return;
    }
    if (typeof errors === 'object' && Array.isArray(Object.values(errors)[0])) {
      Object.keys(errors).forEach((key) => {
        if (Array.isArray(errors[key])) {
          errors[key].forEach((msg: string) => {
            showToast({
              status: 'error',
              message: key,
              description: msg
            });
          });
        } else {
          showToast({
            status: 'error',
            message: key,
            description: errors[key]
          });
        }
      });
      return;
    } else if (typeof errors === 'object' && Object.keys(errors).length <= 1) {
      const values = Object.values(errors)[0];
      showToast({
        status: 'error',
        message: 'Error',
        description: `${values}`
      });
      return;
    } else {
      showToast({
        status: 'error',
        message: 'Error',
        description: errors?.message || defaultError || 'An error occurred.'
      });
      return;
    }
  }

  // Fallback
  showToast({
    status: 'error',
    message: 'Error',
    description: defaultError || 'Oops! Something went wrong.'
  });
}

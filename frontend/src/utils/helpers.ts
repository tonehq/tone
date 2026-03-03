import { showToast } from '@/utils/toast';

export function handleApiError(error: unknown) {
  let message = 'Something went wrong. Please try again.';
  if (typeof error === 'object' && error !== null) {
    const detail = (error as any).response?.data?.detail;
    if (typeof detail === 'string' && detail) {
      message = detail;
    }
  }
  showToast.error(message);
}

export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

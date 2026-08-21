import { isAuthHandled } from '@/utils/authSession';
import { showToast } from '@/utils/toast';

export function handleApiError(error: unknown) {
  // The auth layer (axios interceptor) already surfaced a toast + redirect for
  // expired-session errors; skip so the user doesn't see two toasts.
  if (isAuthHandled(error)) return;

  let message = 'Something went wrong. Please try again.';
  if (typeof error === 'object' && error !== null) {
    const detail = (error as any).response?.data?.detail;
    // FastAPI HTTPExceptions ship `detail` as either:
    //   - a plain string ("Not found")
    //   - a structured object ({code, message}) — used by routers that
    //     surface stable error codes for the UI
    //   - an array of Pydantic validation errors ([{msg, loc, ...}])
    // Read whichever shape is present; fall back to a generic message so a
    // never-mapped error path never hides behind [object Object].
    if (typeof detail === 'string' && detail) {
      message = detail;
    } else if (detail && typeof detail === 'object') {
      if (Array.isArray(detail)) {
        const first = detail.find((d) => typeof d?.msg === 'string');
        if (first?.msg) message = first.msg;
      } else if (typeof (detail as any).message === 'string' && (detail as any).message) {
        message = (detail as any).message;
      }
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

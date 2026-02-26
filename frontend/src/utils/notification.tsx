'use client';

import { Alert, AlertColor, Snackbar } from '@mui/material';
import { useState } from 'react';

// interface NotificationContextType {
//   notify: {
//     success: (title: string, message: string, duration?: number, position?: string) => void;
//     error: (title: string, message: string, duration?: number, position?: string) => void;
//     warning: (title: string, message: string, duration?: number, position?: string) => void;
//     info: (title: string, message: string, duration?: number, position?: string) => void;
//   };
//   contextHolder: React.ReactNode;
// }

export const useNotification = () => {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState<AlertColor>('success');
  const [duration, setDuration] = useState(3000);

  const showNotification = (type: AlertColor, title: string, msg: string, dur: number = 3) => {
    setMessage(`${title}: ${msg}`);
    setSeverity(type);
    setDuration(dur * 1000);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const notify = {
    success: (title: string, message: string, duration?: number) =>
      showNotification('success', title, message, duration),
    error: (title: string, message: string, duration?: number) =>
      showNotification('error', title, message, duration),
    warning: (title: string, message: string, duration?: number) =>
      showNotification('warning', title, message, duration),
    info: (title: string, message: string, duration?: number) =>
      showNotification('info', title, message, duration),
  };

  const contextHolder = (
    <Snackbar
      open={open}
      autoHideDuration={duration}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      <Alert onClose={handleClose} severity={severity} sx={{ width: '100%' }}>
        {message}
      </Alert>
    </Snackbar>
  );

  return { notify, contextHolder };
};

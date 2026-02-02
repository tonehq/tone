'use client';

import React from 'react';
import { Box, SxProps, Theme } from '@mui/material';

interface FormProps {
  children: React.ReactNode;
  onFinish: (values: any) => void;
  sx?: SxProps<Theme>;
  layout?: 'horizontal' | 'vertical';
  autoComplete?: string;
}

export const Form: React.FC<FormProps> = ({
  children,
  onFinish,
  sx,
  layout = 'vertical',
  autoComplete = 'off',
}) => {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const values: Record<string, any> = {};
    formData.forEach((value, key) => {
      values[key] = value;
    });
    onFinish(values);
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      autoComplete={autoComplete}
      sx={{
        display: 'flex',
        flexDirection: layout === 'vertical' ? 'column' : 'row',
        ...sx,
      }}
    >
      {children}
    </Box>
  );
};

export default Form;

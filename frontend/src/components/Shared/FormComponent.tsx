'use client';

import React from 'react';

import { Box, SxProps, Theme } from '@mui/material';

interface FormItemProps {
  name?: string;
  label?: string;
  children: React.ReactNode;
  rules?: Array<{ required?: boolean; message?: string }>;
  className?: string;
}

export const FormItem: React.FC<FormItemProps> = ({ label, children, rules, className }) => (
  <Box sx={{ marginBottom: 2 }} className={className}>
    {label && (
      <Box
        component="label"
        sx={{
          display: 'block',
          marginBottom: 1,
          fontWeight: (theme) => theme.custom.typography.fontWeight.medium,
        }}
      >
        {label}
        {rules?.some((r) => r.required) && <span style={{ color: 'red' }}> *</span>}
      </Box>
    )}
    {children}
  </Box>
);

interface FormProps {
  onFinish?: (values: any) => void;
  className?: string;
  sx?: SxProps<Theme>;
  children: React.ReactNode;
  layout?: 'vertical' | 'horizontal';
  autoComplete?: string;
}

export const Form: React.FC<FormProps> = ({ onFinish, className, sx, children, autoComplete }) => {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const values: any = {};

    // Get all input elements
    const inputs = e.currentTarget.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      const element = input as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
      if (element.name) {
        values[element.name] = element.value;
      }
    });

    onFinish?.(values);
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      className={className}
      sx={sx}
      autoComplete={autoComplete}
    >
      {children}
    </Box>
  );
};

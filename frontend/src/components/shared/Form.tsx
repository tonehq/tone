'use client';

import { cn } from '@/utils/cn';
import React from 'react';

interface FormProps {
  children: React.ReactNode;
  onFinish: (values: any) => void;
  layout?: 'horizontal' | 'vertical';
  autoComplete?: string;
  className?: string;
}

export const Form: React.FC<FormProps> = ({
  children,
  onFinish,
  layout = 'vertical',
  autoComplete = 'off',
  className,
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
    <form
      onSubmit={handleSubmit}
      autoComplete={autoComplete}
      className={cn('space-y-5', layout === 'vertical' ? 'flex-col' : 'flex-row', className)}
    >
      {children}
    </form>
  );
};

export default Form;

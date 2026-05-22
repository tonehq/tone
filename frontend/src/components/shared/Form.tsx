'use client';

import React from 'react';
import type { FieldValues, UseFormHandleSubmit } from 'react-hook-form';

import { cn } from '@/lib/utils';

interface RhfFormProps<T extends FieldValues> {
  children: React.ReactNode;
  onSubmit: (values: T) => void | Promise<void>;
  handleSubmit: UseFormHandleSubmit<T>;
  className?: string;
  autoComplete?: string;
  layout?: 'horizontal' | 'vertical';
  onFinish?: never;
}

interface LegacyFormProps {
  children: React.ReactNode;
  onFinish: (values: Record<string, unknown>) => void;
  className?: string;
  autoComplete?: string;
  layout?: 'horizontal' | 'vertical';
  handleSubmit?: never;
  onSubmit?: never;
}

type FormProps<T extends FieldValues> = RhfFormProps<T> | LegacyFormProps;

function isRhfForm<T extends FieldValues>(props: FormProps<T>): props is RhfFormProps<T> {
  return typeof (props as RhfFormProps<T>).handleSubmit === 'function';
}

export function Form<T extends FieldValues>(props: FormProps<T>) {
  const { children, className, autoComplete = 'off', layout = 'vertical' } = props;

  if (isRhfForm(props)) {
    const { handleSubmit, onSubmit } = props;
    return (
      <form
        onSubmit={handleSubmit(onSubmit)}
        autoComplete={autoComplete}
        className={cn('space-y-4', layout === 'horizontal' && 'flex-row', className)}
      >
        {children}
      </form>
    );
  }

  const { onFinish } = props as LegacyFormProps;
  const submit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const values: Record<string, unknown> = {};
    formData.forEach((value, key) => {
      values[key] = value;
    });
    onFinish(values);
  };
  return (
    <form
      onSubmit={submit}
      autoComplete={autoComplete}
      className={cn('space-y-5', layout === 'horizontal' && 'flex-row', className)}
    >
      {children}
    </form>
  );
}

export default Form;

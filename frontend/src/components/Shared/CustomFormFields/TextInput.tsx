'use client';

import React, { FC, memo, useState } from 'react';

import { Box, IconButton, InputAdornment, Skeleton, TextField } from '@mui/material';
import { Eye, EyeOff } from 'lucide-react';

import { FormItem } from '@/components/shared/FormComponent';

interface TextInputProps {
  name: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search';
  label?: string;
  placeholder?: string;
  defaultValue?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  className?: string;
  inputClassName?: string;
  isRequired?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  autoComplete?: string;
  showPasswordToggle?: boolean;
  rules?: Array<{ required?: boolean; message?: string }>;
  withFormItem?: boolean;
  loading?: boolean;
  InputProps?: {
    startAdornment?: React.ReactNode;
    endAdornment?: React.ReactNode;
  };
}

const TextInput: FC<TextInputProps> = memo(
  ({
    name,
    type = 'text',
    label,
    placeholder,
    defaultValue,
    value,
    onChange,
    className,
    inputClassName,
    isRequired = false,
    disabled = false,
    error = false,
    helperText,
    fullWidth = true,
    autoComplete,
    showPasswordToggle = type === 'password',
    rules,
    withFormItem = true,
    loading = false,
    InputProps,
  }) => {
    const [showPassword, setShowPassword] = useState(false);

    const handleClickShowPassword = () => {
      setShowPassword(!showPassword);
    };

    const handleMouseDownPassword = (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
    };

    // Determine autoComplete if not provided
    const getAutoComplete = () => {
      if (autoComplete) return autoComplete;
      switch (type) {
        case 'email':
          return 'email';
        case 'password':
          return 'current-password';
        default:
          return 'off';
      }
    };

    // Determine input type for password field
    const inputType = type === 'password' && showPassword ? 'text' : type;

    const skeleton = (
      <Skeleton variant="rectangular" width="100%" height={42} sx={{ borderRadius: '5px' }} />
    );

    const inputField = (
      <TextField
        name={name}
        type={inputType}
        placeholder={placeholder}
        defaultValue={defaultValue}
        value={value}
        onChange={onChange}
        required={isRequired}
        disabled={disabled}
        error={error}
        helperText={helperText}
        fullWidth={fullWidth}
        autoComplete={getAutoComplete()}
        variant="outlined"
        className={inputClassName}
        InputProps={{
          ...(InputProps || {}),
          ...(showPasswordToggle && type === 'password'
            ? {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleClickShowPassword}
                      onMouseDown={handleMouseDownPassword}
                      edge="end"
                      sx={{
                        color: '#6b7280',
                        '&:hover': {
                          backgroundColor: 'rgba(0, 0, 0, 0.04)',
                        },
                      }}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </IconButton>
                  </InputAdornment>
                ),
              }
            : {}),
        }}
        sx={{
          '& .MuiOutlinedInput-root': {
            height: '42px',
            backgroundColor: '#f9fafb',
            borderRadius: '5px',
            fontSize: (theme) => theme.custom.typography.fontSize.base,
            '& fieldset': {
              borderColor: error ? '#ef4444' : '#e2e8f0',
              borderWidth: '1px',
            },
            '&:hover fieldset': {
              borderColor: error ? '#ef4444' : '#60a5fa',
            },
            '&.Mui-focused fieldset': {
              borderColor: error ? '#ef4444' : '#60a5fa',
              borderWidth: '1px',
            },
            '&.Mui-disabled': {
              backgroundColor: '#f3f4f6',
            },
          },
          '& .MuiInputBase-input': {
            paddingRight: showPasswordToggle && type === 'password' ? '40px' : '14px',
          },
          '& .MuiFormHelperText-root': {
            marginTop: '4px',
            fontSize: (theme) => theme.custom.typography.fontSize.xs,
          },
        }}
      />
    );

    // If withFormItem is true, wrap with FormItem
    if (withFormItem) {
      return (
        <FormItem
          name={name}
          label={label}
          rules={rules || (isRequired ? [{ required: true }] : [])}
          className={className}
        >
          {loading ? skeleton : inputField}
        </FormItem>
      );
    }

    // Otherwise, just return the input field
    return <Box className={className}>{loading ? skeleton : inputField}</Box>;
  },
);

TextInput.displayName = 'TextInput';

export { TextInput };

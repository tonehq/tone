'use client';

import { FC, memo } from 'react';

import { Box, FormControl, MenuItem, Select, SelectChangeEvent, Skeleton } from '@mui/material';

import { FormItem } from '@/components/shared/FormComponent';

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

interface SelectInputProps {
  name: string;
  label?: string;
  placeholder?: string;
  defaultValue?: string | number;
  value?: string | number;
  onChange?: (e: SelectChangeEvent<string | number>) => void;
  options: SelectOption[];
  className?: string;
  inputClassName?: string;
  isRequired?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  size?: 'small' | 'medium';
  variant?: 'standard' | 'outlined' | 'filled';
  disableUnderline?: boolean;
  rules?: Array<{ required?: boolean; message?: string }>;
  withFormItem?: boolean;
  loading?: boolean;
}

const SelectInput: FC<SelectInputProps> = memo(
  ({
    name,
    label,
    placeholder,
    defaultValue,
    value,
    onChange,
    options,
    className,
    inputClassName,
    isRequired = false,
    disabled = false,
    error = false,
    helperText,
    fullWidth = true,
    size = 'medium',
    variant = 'outlined',
    disableUnderline = false,
    rules,
    withFormItem = true,
    loading = false,
  }) => {
    const skeleton = (
      <Skeleton variant="rectangular" width="100%" height={42} sx={{ borderRadius: '5px' }} />
    );

    const selectField = (
      <FormControl
        fullWidth={fullWidth}
        error={error}
        disabled={disabled}
        size={size}
        variant={variant}
        className={inputClassName}
        sx={{
          '& .MuiOutlinedInput-root': {
            height: variant === 'outlined' ? '42px' : 'auto',
            backgroundColor: variant === 'outlined' ? '#f9fafb' : 'transparent',
            borderRadius: '5px',
            fontSize: '16px',
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
            padding: variant === 'outlined' ? '10px 14px' : '4px 8px',
          },
          '& .MuiFormHelperText-root': {
            marginTop: '4px',
            fontSize: '12px',
          },
          ...(variant === 'standard' &&
            disableUnderline && {
              '& .MuiInput-underline:before': {
                borderBottom: 'none',
              },
              '& .MuiInput-underline:hover:before': {
                borderBottom: 'none',
              },
              '& .MuiInput-underline:after': {
                borderBottom: 'none',
              },
              '& .MuiInput-root': {
                border: `1px solid ${error ? '#ef4444' : '#e2e8f0'}`,
                borderRadius: '5px',
                padding: '4px 8px',
                backgroundColor: '#f9fafb',
                '&:hover': {
                  borderColor: error ? '#ef4444' : '#60a5fa',
                },
                '&.Mui-focused': {
                  borderColor: error ? '#ef4444' : '#60a5fa',
                },
                '&.Mui-disabled': {
                  backgroundColor: '#f3f4f6',
                  borderColor: '#e2e8f0',
                },
              },
            }),
        }}
      >
        <Select
          name={name}
          value={value ?? defaultValue ?? ''}
          onChange={onChange}
          disabled={disabled}
          displayEmpty={!!placeholder}
          renderValue={(selected) => {
            if (!selected && placeholder) return placeholder;
            const selectedOption = options.find((option) => option.value === selected);
            return selectedOption ? selectedOption.label : selected || '';
          }}
          sx={{
            fontSize: '14px',
            ...(variant === 'standard' && {
              '& .MuiSelect-select': {
                padding: '0',
                paddingRight: '24px',
              },
            }),
          }}
        >
          {placeholder && (
            <MenuItem value="" disabled>
              {placeholder}
            </MenuItem>
          )}
          {options.map((option) => (
            <MenuItem key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
        {helperText && variant === 'outlined' && (
          <Box sx={{ fontSize: '12px', color: error ? '#ef4444' : '#6b7280', marginTop: '4px' }}>
            {helperText}
          </Box>
        )}
      </FormControl>
    );

    if (withFormItem) {
      return (
        <FormItem
          name={name}
          label={label}
          rules={rules || (isRequired ? [{ required: true }] : [])}
          className={className}
        >
          {loading ? skeleton : selectField}
        </FormItem>
      );
    }

    return <Box className={className}>{loading ? skeleton : selectField}</Box>;
  },
);

SelectInput.displayName = 'SelectInput';

export { SelectInput };

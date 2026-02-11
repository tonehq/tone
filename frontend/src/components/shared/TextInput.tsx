'use client';

import {
    Box,
    IconButton,
    InputAdornment,
    Skeleton,
    TextField,
    Typography,
    useTheme,
} from '@mui/material';
import { Eye, EyeOff } from 'lucide-react';
import React, { forwardRef, useState } from 'react';

interface TextInputProps {
  name: string;
  type?: string;
  label?: string;
  placeholder?: string;
  value?: string;
  defaultValue?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isRequired?: boolean;
  rules?: any[];
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  fullWidth?: boolean;
  withFormItem?: boolean;
  className?: string;
  InputProps?: any;
}

const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  (
    {
      name,
      type = 'text',
      label,
      placeholder,
      value,
      defaultValue,
      onChange,
      isRequired = false,
      loading = false,
      disabled = false,
      error = false,
      helperText,
      fullWidth = true,
      InputProps,
    },
    ref,
  ) => {
    const theme = useTheme();
    const [showPassword, setShowPassword] = useState(false);
    const showPasswordToggle = type === 'password';

    const handleClickShowPassword = () => setShowPassword(!showPassword);
    const handleMouseDownPassword = (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault();
    };

    const skeleton = (
      <Box>
        <Skeleton variant="text" width={80} height={20} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" height={42} sx={{ borderRadius: 1 }} />
      </Box>
    );

    const inputField = (
      <Box sx={{ mb: 2 }}>
        {label && (
          <Typography
            component="label"
            sx={{
              display: 'block',
              mb: 0.5,
              fontSize: theme.custom.typography.fontSize.sm,
              fontWeight: theme.custom.typography.fontWeight.medium,
              color: theme.palette.text.primary,
            }}
          >
            {label}
            {isRequired && (
              <Typography component="span" sx={{ color: theme.palette.error.main, ml: 0.5 }}>
                *
              </Typography>
            )}
          </Typography>
        )}
        <TextField
          inputRef={ref}
          name={name}
          type={showPasswordToggle ? (showPassword ? 'text' : 'password') : type}
          placeholder={placeholder}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          disabled={disabled}
          error={error}
          helperText={helperText}
          fullWidth={fullWidth}
          size="small"
          InputProps={{
            ...InputProps,
            ...(showPasswordToggle
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
              fontSize: theme.custom.typography.fontSize.base,
              '& fieldset': {
                borderColor: error ? '#ef4444' : '#e2e8f0',
                borderWidth: '1px',
              },
              '&:hover fieldset': {
                borderColor: error ? '#ef4444' : '#60a5fa',
              },
              '&.Mui-focused fieldset': {
                borderColor: error ? '#ef4444' : '#8b5cf6',
                borderWidth: '1px',
              },
              '&.Mui-disabled': {
                backgroundColor: '#f3f4f6',
              },
            },
            '& .MuiInputBase-input': {
              paddingRight: showPasswordToggle ? '40px' : '14px',
            },
            '& .MuiFormHelperText-root': {
              marginTop: '4px',
              fontSize: theme.custom.typography.fontSize.xs,
            },
          }}
        />
      </Box>
    );

    return loading ? skeleton : inputField;
  },
);

TextInput.displayName = 'TextInput';

export { TextInput };
export default TextInput;

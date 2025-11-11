'use client';

import { createTheme } from '@mui/material/styles';

// Typography tokens - utility system
const typographyTokens = {
  fontSize: {
    xs: '0.75rem', // 12px
    sm: '0.875rem', // 14px
    base: '1rem', // 16px
    lg: '1.125rem', // 18px
    xl: '1.25rem', // 20px
    '2xl': '1.5rem', // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
    '5xl': '3rem', // 48px
  },
  // Font weights
  fontWeight: {
    thin: 100,
    extralight: 200,
    light: 300,
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
    black: 900,
  },
  // Line heights
  lineHeight: {
    none: 1,
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },
};

// Border radius tokens - utility system
const borderRadiusTokens = {
  none: '0px',
  sm: '2px',
  base: '5px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '20px',
  full: '9999px',
};

// Create Material UI theme with actual color values (MUI doesn't support CSS vars in palette)
export const muiTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1d4ed8',
      dark: '#1e40af',
      light: '#3b82f6',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#9333EA',
      dark: '#7e22ce',
      light: '#a855f7',
      contrastText: '#ffffff',
    },
    success: {
      main: '#52c41a',
      dark: '#389e0d',
      light: '#73d13d',
    },
    warning: {
      main: '#faad14',
      dark: '#d48806',
      light: '#ffc53d',
    },
    error: {
      main: '#f5222d',
      dark: '#cf1322',
      light: '#ff4d4f',
    },
    text: {
      primary: '#111827',
      secondary: '#6b7280',
      disabled: '#d1d5db',
    },
    background: {
      default: '#ffffff',
      paper: '#f9fafb',
    },
    divider: '#e2e8f0',
    grey: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
  },
  // Custom tokens - includes button styles and typography tokens
  custom: {
    button: {
      active: {
        backgroundColor: '#1d4ed8', // Uses palette.primary.main
        color: '#ffffff',
        hover: {
          backgroundColor: '#1e40af', // Uses palette.primary.dark
        },
        disabled: {
          backgroundColor: '#1d4ed8', // Uses palette.primary.main
          color: '#ffffff',
          opacity: 0.7,
        },
      },
      inactive: {
        backgroundColor: '#ffffff', // Uses palette.background.default
        color: '#334155', // Uses palette.grey[700]
        borderColor: '#e2e8f0', // Uses palette.grey[200]
        disabled: {
          backgroundColor: '#ffffff',
          color: '#334155',
          opacity: 0.7,
        },
      },
      spinner: {
        active: '#ffffff',
        inactive: '#334155',
      },
    },
    // Typography tokens (Tailwind-like)
    typography: typographyTokens,
    // Border radius tokens (Tailwind-like)
    borderRadius: borderRadiusTokens,
  },
  typography: {
    fontFamily:
      'Roobert, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"',
    fontSize: 16,
    h1: {
      fontSize: typographyTokens.fontSize['4xl'],
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    h2: {
      fontSize: typographyTokens.fontSize['3xl'],
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    h3: {
      fontSize: typographyTokens.fontSize['2xl'],
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    h4: {
      fontSize: typographyTokens.fontSize.xl,
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    h5: {
      fontSize: typographyTokens.fontSize.lg,
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    h6: {
      fontSize: typographyTokens.fontSize.base,
      fontWeight: typographyTokens.fontWeight.semibold,
    },
    body1: {
      fontSize: typographyTokens.fontSize.base,
    },
    body2: {
      fontSize: typographyTokens.fontSize.sm,
    },
  },
  shape: {
    borderRadius: 5, // Use base borderRadius token value
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
          textTransform: 'none',
          fontWeight: typographyTokens.fontWeight.medium,
          fontSize: typographyTokens.fontSize.sm,
          padding: '8px 16px',
          height: '36px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        contained: {
          '&.MuiButton-containedPrimary': {
            backgroundColor: '#1d4ed8',
            '&:hover': {
              backgroundColor: '#1e40af',
            },
          },
        },
        text: {
          '&:hover': {
            backgroundColor: '#f9fafb',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: borderRadiusTokens.base,
            fontSize: typographyTokens.fontSize.sm,
            '& fieldset': {
              borderColor: '#e2e8f0',
            },
            '&:hover fieldset': {
              borderColor: '#cbd5e1',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#e2e8f0',
              borderWidth: '1px',
            },
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
          fontSize: typographyTokens.fontSize.sm,
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: '#e2e8f0',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#cbd5e1',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
        },
        elevation1: {
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        },
        elevation2: {
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
          fontSize: typographyTokens.fontSize.sm,
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: {
          borderRadius: borderRadiusTokens.base,
          border: '1px solid #e2e8f0',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            backgroundColor: '#f9fafb',
            fontWeight: typographyTokens.fontWeight.semibold,
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: '#e2e8f0',
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: borderRadiusTokens.base,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          padding: '8px 16px',
          fontSize: typographyTokens.fontSize.sm,
          '&:hover': {
            backgroundColor: '#f9fafb',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: borderRadiusTokens.base,
        },
      },
    },
    MuiBreadcrumbs: {
      styleOverrides: {
        separator: {
          margin: '0 4px',
        },
      },
    },
  },
});

// Export typography and borderRadius tokens for direct use in components
export { borderRadiusTokens, typographyTokens };

'use client';

import { createTheme } from '@mui/material/styles';

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
  // Custom button colors accessible via theme.custom
  // Note: active button colors use palette.primary for consistency
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
  },
  typography: {
    fontFamily:
      'Roobert, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"',
    fontSize: 16,
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: 16,
    },
    body2: {
      fontSize: 14,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 5,
          textTransform: 'none',
          fontWeight: 500,
          fontSize: 14,
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
            borderRadius: 5,
            fontSize: 14,
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
          borderRadius: 5,
          fontSize: 14,
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
          borderRadius: 8,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
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
          borderRadius: 5,
          fontSize: 14,
        },
      },
    },
    MuiTableContainer: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          border: '1px solid #e2e8f0',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            backgroundColor: '#f9fafb',
            fontWeight: 600,
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
          borderRadius: 8,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          padding: '8px 16px',
          fontSize: 14,
          '&:hover': {
            backgroundColor: '#f9fafb',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 8,
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

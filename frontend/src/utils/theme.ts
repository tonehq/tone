'use client';

import { createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Theme {
    custom: {
      typography: {
        fontSize: {
          xs: string;
          sm: string;
          base: string;
          lg: string;
          xl: string;
        };
        fontWeight: {
          normal: number;
          medium: number;
          semibold: number;
          bold: number;
        };
      };
      borderRadius: {
        sm: string;
        base: string;
        md: string;
        lg: string;
      };
    };
  }
  interface ThemeOptions {
    custom?: {
      typography?: {
        fontSize?: {
          xs?: string;
          sm?: string;
          base?: string;
          lg?: string;
          xl?: string;
        };
        fontWeight?: {
          normal?: number;
          medium?: number;
          semibold?: number;
          bold?: number;
        };
      };
      borderRadius?: {
        sm?: string;
        base?: string;
        md?: string;
        lg?: string;
      };
    };
  }
}

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#8b5cf6',
      dark: '#7c3aed',
      light: '#a78bfa',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#6366f1',
      dark: '#4f46e5',
      light: '#818cf8',
      contrastText: '#ffffff',
    },
    success: {
      main: '#10b981',
      dark: '#059669',
      light: '#34d399',
    },
    warning: {
      main: '#f59e0b',
      dark: '#d97706',
      light: '#fbbf24',
    },
    error: {
      main: '#ef4444',
      dark: '#dc2626',
      light: '#f87171',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
      disabled: '#d1d5db',
    },
    background: {
      default: '#f9fafb',
      paper: '#ffffff',
    },
    divider: '#e2e8f0',
  },
  typography: {
    fontFamily: '"Inter", "Roobert", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    h1: {
      fontSize: '2.25rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '1.875rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.125rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '15px',
    },
    body2: {
      fontSize: '14px',
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  custom: {
    typography: {
      fontSize: {
        xs: '0.75rem',
        sm: '0.8125rem',
        base: '0.875rem',
        lg: '1rem',
        xl: '1.125rem',
      },
      fontWeight: {
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
      },
    },
    borderRadius: {
      sm: '4px',
      base: '8px',
      md: '12px',
      lg: '16px',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          fontWeight: 500,
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: {
          minHeight: 44,
        },
        indicator: {
          backgroundColor: '#8b5cf6',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          minHeight: 44,
          textTransform: 'none',
          fontWeight: 500,
          '&.Mui-selected': {
            color: '#8b5cf6',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
  },
});

export default theme;

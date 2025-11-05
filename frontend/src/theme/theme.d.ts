import '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Theme {
    custom: {
      button: {
        active: {
          backgroundColor: string;
          color: string;
          hover: {
            backgroundColor: string;
          };
          disabled: {
            backgroundColor: string;
            color: string;
            opacity: number;
          };
        };
        inactive: {
          backgroundColor: string;
          color: string;
          borderColor: string;
          disabled: {
            backgroundColor: string;
            color: string;
            opacity: number;
          };
        };
        spinner: {
          active: string;
          inactive: string;
        };
      };
    };
  }

  interface ThemeOptions {
    custom?: {
      button?: {
        active?: {
          backgroundColor?: string;
          color?: string;
          hover?: {
            backgroundColor?: string;
          };
          disabled?: {
            backgroundColor?: string;
            color?: string;
            opacity?: number;
          };
        };
        inactive?: {
          backgroundColor?: string;
          color?: string;
          borderColor?: string;
          disabled?: {
            backgroundColor?: string;
            color?: string;
            opacity?: number;
          };
        };
        spinner?: {
          active?: string;
          inactive?: string;
        };
      };
    };
  }
}

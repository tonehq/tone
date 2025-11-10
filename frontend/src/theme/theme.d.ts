import '@mui/material/styles';

// Typography token types
export interface TypographyTokens {
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
    '4xl': string;
    '5xl': string;
  };
  fontWeight: {
    thin: number;
    extralight: number;
    light: number;
    normal: number;
    medium: number;
    semibold: number;
    bold: number;
    extrabold: number;
    black: number;
  };
  lineHeight: {
    none: number;
    tight: number;
    snug: number;
    normal: number;
    relaxed: number;
    loose: number;
  };
}

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
      typography: TypographyTokens;
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
      typography?: TypographyTokens;
    };
  }
}

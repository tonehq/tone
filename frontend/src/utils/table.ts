export interface DynamicScrollConfig {
  useCSSHeight?: boolean;
  cssHeight?: string;
  fallbackHeight?: number;
}

const DEFAULT_SCROLL_CONFIG: Required<DynamicScrollConfig> = {
  useCSSHeight: true,
  cssHeight: 'calc(100vh - 400px)',
  fallbackHeight: 400,
};

export const useDynamicScrollHeight = (
  scrollY: number | string | undefined,
  config: DynamicScrollConfig = {},
): number | string | undefined => {
  const finalConfig = { ...DEFAULT_SCROLL_CONFIG, ...config };

  if (typeof scrollY === 'string') {
    return scrollY;
  }

  if (finalConfig.useCSSHeight && finalConfig.cssHeight) {
    return finalConfig.cssHeight;
  }

  return scrollY || finalConfig.fallbackHeight;
};

export const calculateScrollHeight = (
  scrollY: number | string | undefined,
  config: DynamicScrollConfig = {},
): number | string | undefined => {
  const finalConfig = { ...DEFAULT_SCROLL_CONFIG, ...config };

  if (typeof scrollY === 'string') {
    return scrollY;
  }

  if (finalConfig.useCSSHeight && finalConfig.cssHeight) {
    return finalConfig.cssHeight;
  }

  return scrollY || finalConfig.fallbackHeight;
};

export const CSS_HEIGHT_PRESETS = {
  SETTINGS: 'calc(100vh - 420px)',
} as const;

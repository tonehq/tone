// ── Semantic Color Classes ──────────────────────────────────────────────────
export const semantic = {
  primary: 'primary',
  primaryForeground: 'primary-foreground',

  secondary: 'secondary',
  secondaryForeground: 'secondary-foreground',

  destructive: 'destructive',
  destructiveForeground: 'destructive-foreground',

  muted: 'muted',
  mutedForeground: 'muted-foreground',

  accent: 'accent',
  accentForeground: 'accent-foreground',

  background: 'background',
  foreground: 'foreground',

  card: 'card',
  cardForeground: 'card-foreground',

  popover: 'popover',
  popoverForeground: 'popover-foreground',

  border: 'border',
  input: 'input',
  ring: 'ring',

  sidebar: 'sidebar',
  sidebarForeground: 'sidebar-foreground',
  sidebarAccent: 'sidebar-accent',
} as const;

// ── Component Class Presets ──────────────────────────────────────────────────
// Pre-built class strings for common UI patterns. Use with cn():
//   cn(presets.button.base, presets.button.primary, className)
export const presets = {
  button: {
    base: 'inline-flex items-center justify-center rounded-lg font-medium text-sm transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    outline:
      'border border-input bg-background text-foreground hover:bg-accent hover:text-accent-foreground',
    ghost: 'text-foreground hover:bg-accent hover:text-accent-foreground',
    destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    link: 'text-primary underline-offset-4 hover:underline',
    size: {
      sm: 'h-8 px-3 text-xs',
      md: 'h-9 px-4 text-sm',
      lg: 'h-10 px-6 text-sm',
    },
  },
  input: {
    base: 'flex w-full rounded-lg border border-input bg-transparent text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
    size: {
      sm: 'h-8 px-2.5 text-xs',
      md: 'h-9 px-3 text-sm',
      lg: 'h-10 px-4 text-sm',
    },
  },
  card: {
    base: 'rounded-lg bg-card shadow-sm border border-border',
    padded: 'rounded-lg bg-card shadow-sm border border-border p-6',
  },
  badge: {
    base: 'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium',
    default: 'bg-secondary text-secondary-foreground',
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-50 text-green-600',
    warning: 'bg-amber-50 text-amber-600',
    destructive: 'bg-destructive/10 text-destructive',
  },
  text: {
    heading: 'text-lg font-semibold text-foreground',
    body: 'text-sm text-foreground',
    secondary: 'text-sm text-muted-foreground',
    label: 'text-sm font-medium text-foreground',
  },
  focus: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
} as const;

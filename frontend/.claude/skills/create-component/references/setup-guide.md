# shadcn/ui + Tailwind CSS — First-Time Setup Guide

This guide sets up shadcn/ui and Tailwind CSS v4 in the existing Next.js project alongside MUI.
Run this **once** per project. After setup, all new shared components use shadcn/Tailwind.

---

## Prerequisites

- Node.js 18+
- yarn (package manager — this project uses yarn, NOT npm)
- Next.js 15 with App Router (already in place)

---

## Step 1 — Install Tailwind CSS v4

Tailwind CSS v4 uses a new CSS-first configuration approach.

```bash
cd frontend
yarn add tailwindcss @tailwindcss/postcss
```

---

## Step 2 — Configure PostCSS

Create or update `frontend/postcss.config.mjs`:

```javascript
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};

export default config;
```

---

## Step 3 — Add Tailwind to globals.css

Add the Tailwind import at the **top** of `frontend/src/app/globals.css`:

```css
@import 'tailwindcss';
```

Then add the theme CSS variables. These use **hex values organized by color family** — the same approach as the tone-test project. All values map from the existing MUI theme in `src/utils/theme.ts`.

```css
:root {
  /* ── Purple (Primary) ──────────────────────────────────────── */
  --purple_50: #f5f3ff;
  --purple_100: #ede9fe;
  --purple_200: #ddd6fe;
  --purple_300: #c4b5fd;
  --purple_400: #a78bfa;          /* palette.primary.light */
  --purple_500: #8b5cf6;          /* palette.primary.main */
  --purple_600: #7c3aed;          /* palette.primary.dark */
  --purple_700: #6d28d9;
  --purple_800: #5b21b6;
  --purple_900: #4c1d95;

  /* ── Indigo (Secondary) ────────────────────────────────────── */
  --indigo_50: #eef2ff;
  --indigo_100: #e0e7ff;
  --indigo_200: #c7d2fe;
  --indigo_300: #a5b4fc;
  --indigo_400: #818cf8;          /* palette.secondary.light */
  --indigo_500: #6366f1;          /* palette.secondary.main */
  --indigo_600: #4f46e5;          /* palette.secondary.dark */
  --indigo_700: #4338ca;
  --indigo_800: #3730a3;
  --indigo_900: #312e81;

  /* ── Green (Success) ───────────────────────────────────────── */
  --green_50: #ecfdf5;
  --green_100: #d1fae5;
  --green_200: #a7f3d0;
  --green_300: #6ee7b7;
  --green_400: #34d399;           /* palette.success.light */
  --green_500: #10b981;           /* palette.success.main */
  --green_600: #059669;           /* palette.success.dark */
  --green_700: #047857;
  --green_800: #065f46;
  --green_900: #064e3b;

  /* ── Amber (Warning) ───────────────────────────────────────── */
  --amber_50: #fffbeb;
  --amber_100: #fef3c7;
  --amber_200: #fde68a;
  --amber_300: #fcd34d;
  --amber_400: #fbbf24;           /* palette.warning.light */
  --amber_500: #f59e0b;           /* palette.warning.main */
  --amber_600: #d97706;           /* palette.warning.dark */
  --amber_700: #b45309;
  --amber_800: #92400e;
  --amber_900: #78350f;

  /* ── Red (Error / Destructive) ─────────────────────────────── */
  --red_50: #fef2f2;
  --red_100: #fee2e2;
  --red_200: #fecaca;
  --red_300: #fca5a5;
  --red_400: #f87171;             /* palette.error.light */
  --red_500: #ef4444;             /* palette.error.main */
  --red_600: #dc2626;             /* palette.error.dark */
  --red_700: #b91c1c;
  --red_800: #991b1b;
  --red_900: #7f1d1d;

  /* ── Gray (Text, Backgrounds) ──────────────────────────────── */
  --gray_50: #f9fafb;             /* palette.background.default */
  --gray_100: #f3f4f6;
  --gray_200: #e5e7eb;
  --gray_300: #d1d5db;            /* palette.text.disabled */
  --gray_400: #9ca3af;
  --gray_500: #6b7280;            /* palette.text.secondary */
  --gray_600: #4b5563;
  --gray_700: #374151;
  --gray_800: #1f2937;            /* palette.text.primary */
  --gray_900: #111827;

  /* ── Slate (Borders, Dividers) ─────────────────────────────── */
  --slate_50: #f8fafc;
  --slate_100: #f1f5f9;
  --slate_200: #e2e8f0;           /* palette.divider */
  --slate_300: #cbd5e1;
  --slate_400: #94a3b8;

  /* ── White ─────────────────────────────────────────────────── */
  --white: #ffffff;               /* palette.background.paper */

  /* ── Shadows ───────────────────────────────────────────────── */
  --shadow-xs: 0 1px 2px 0 rgba(16, 24, 40, 0.05);
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);

  /* ── Border Radius ─────────────────────────────────────────── */
  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 5px;               /* shape.borderRadius — project default */
  --radius-lg: 8px;
  --radius-xl: 10px;
  --radius-2xl: 12px;

  /* ── Spacing ───────────────────────────────────────────────── */
  --space-xs: 2px;
  --space-sm: 4px;
  --space-md: 6px;
  --space-lg: 8px;
  --space-xl: 10px;
  --space-2xl: 12px;
  --space-3xl: 14px;
  --space-4xl: 16px;
  --space-5xl: 18px;
  --space-6xl: 20px;
  --space-7xl: 24px;
  --space-8xl: 32px;
}
```

**IMPORTANT**: Preserve all existing CSS rules in `globals.css`. Add the Tailwind import at the very top and the CSS variables after existing rules, or in a section clearly marked.

---

## Step 3b — Create Tailwind config with color palette

Create `frontend/tailwind.config.ts` that maps CSS variables to Tailwind color classes.
This follows the same pattern as the tone-test project — every color references a CSS variable.

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontSize: {
        xs: '0.75rem',       // 12px
        sm: '0.8125rem',     // 13px — project custom
        base: '0.875rem',    // 14px — project custom
        lg: '1rem',          // 16px
        xl: '1.125rem',      // 18px
        '2xl': '1.5rem',     // 24px
        '3xl': '1.875rem',   // 30px
        '4xl': '2.25rem',    // 36px
      },
      colors: {
        purple: {
          50: 'var(--purple_50)',
          100: 'var(--purple_100)',
          200: 'var(--purple_200)',
          300: 'var(--purple_300)',
          400: 'var(--purple_400)',
          500: 'var(--purple_500)',
          600: 'var(--purple_600)',
          700: 'var(--purple_700)',
          800: 'var(--purple_800)',
          900: 'var(--purple_900)',
        },
        indigo: {
          50: 'var(--indigo_50)',
          100: 'var(--indigo_100)',
          200: 'var(--indigo_200)',
          300: 'var(--indigo_300)',
          400: 'var(--indigo_400)',
          500: 'var(--indigo_500)',
          600: 'var(--indigo_600)',
          700: 'var(--indigo_700)',
          800: 'var(--indigo_800)',
          900: 'var(--indigo_900)',
        },
        green: {
          50: 'var(--green_50)',
          100: 'var(--green_100)',
          200: 'var(--green_200)',
          300: 'var(--green_300)',
          400: 'var(--green_400)',
          500: 'var(--green_500)',
          600: 'var(--green_600)',
          700: 'var(--green_700)',
          800: 'var(--green_800)',
          900: 'var(--green_900)',
        },
        amber: {
          50: 'var(--amber_50)',
          100: 'var(--amber_100)',
          200: 'var(--amber_200)',
          300: 'var(--amber_300)',
          400: 'var(--amber_400)',
          500: 'var(--amber_500)',
          600: 'var(--amber_600)',
          700: 'var(--amber_700)',
          800: 'var(--amber_800)',
          900: 'var(--amber_900)',
        },
        red: {
          50: 'var(--red_50)',
          100: 'var(--red_100)',
          200: 'var(--red_200)',
          300: 'var(--red_300)',
          400: 'var(--red_400)',
          500: 'var(--red_500)',
          600: 'var(--red_600)',
          700: 'var(--red_700)',
          800: 'var(--red_800)',
          900: 'var(--red_900)',
        },
        gray: {
          50: 'var(--gray_50)',
          100: 'var(--gray_100)',
          200: 'var(--gray_200)',
          300: 'var(--gray_300)',
          400: 'var(--gray_400)',
          500: 'var(--gray_500)',
          600: 'var(--gray_600)',
          700: 'var(--gray_700)',
          800: 'var(--gray_800)',
          900: 'var(--gray_900)',
        },
        slate: {
          50: 'var(--slate_50)',
          100: 'var(--slate_100)',
          200: 'var(--slate_200)',
          300: 'var(--slate_300)',
          400: 'var(--slate_400)',
        },
        white: 'var(--white)',
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
      borderRadius: {
        xs: 'var(--radius-xs)',
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
```

### How it works

- Every color is a **CSS variable reference** (e.g., `var(--purple_500)`)
- Changing a color in `:root` automatically updates every Tailwind class that uses it
- No HSL conversion needed — uses direct hex values
- The shade scale (50–900) follows the same pattern as the tone-test project

### Usage in components

```typescript
// Primary button — purple palette
className="bg-purple-500 text-white hover:bg-purple-600"

// Secondary action — indigo palette
className="bg-indigo-500 text-white hover:bg-indigo-600"

// Error state — red palette
className="bg-red-500 text-white hover:bg-red-600"

// Text colors — gray palette
className="text-gray-800"   // primary text
className="text-gray-500"   // secondary text

// Borders — slate palette
className="border-slate-200" // divider
```

---

## Step 4 — Install shadcn/ui dependencies

```bash
cd frontend
yarn add class-variance-authority clsx tailwind-merge
```

### What each package does

| Package | Purpose |
|---------|---------|
| `clsx` | Conditional className composition — accepts strings, objects, arrays, and strips falsy values |
| `tailwind-merge` | Resolves Tailwind CSS class conflicts — `twMerge('px-4', 'px-2')` → `'px-2'` (last wins) |
| `class-variance-authority` | Type-safe variant management for components with multiple visual states (CVA) |

Together, `clsx` + `tailwind-merge` form the `cn()` utility. CVA uses `cn()` internally for variant class application.

---

## Step 5 — Create the `cn()` utility and theme constants

### 5a. Create `src/lib/utils.ts`

Create `frontend/src/lib/utils.ts`:

```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### How `cn()` works

`cn()` chains two functions:

1. **`clsx(...inputs)`** — Accepts strings, objects, arrays, and falsy values. Returns a
   single class string with all falsy values (`false`, `undefined`, `null`, `0`, `''`) removed.

2. **`twMerge(classString)`** — Takes the class string from clsx and resolves Tailwind CSS
   conflicts. When two classes target the same CSS property, the **last one wins**.

### Why both are needed

```typescript
// clsx alone — falsy removal, object/array support, but NO conflict resolution
clsx('bg-primary', 'bg-red-500')          // → 'bg-primary bg-red-500' (BOTH applied)

// twMerge alone — conflict resolution, but NO object/array/falsy support
twMerge('bg-primary', 'bg-red-500')       // → 'bg-red-500' (correct)
twMerge({ 'bg-red-500': true })           // ERROR: doesn't accept objects

// cn() — best of both
cn('bg-primary', { 'bg-red-500': true })  // → 'bg-red-500' (correct)
cn('px-4', false && 'px-2', 'mt-4')       // → 'px-4 mt-4' (correct)
```

### Quick usage examples

```typescript
// Static classes
cn('flex items-center gap-2')

// Conditional via object
cn('base', { 'bg-primary': isActive, 'opacity-50': disabled })

// Conditional via short-circuit
cn('base', isActive && 'bg-primary', disabled && 'opacity-50')

// Consumer override (className prop always last)
cn('bg-primary text-white', className)
// If className='bg-red-500', twMerge resolves → 'bg-red-500 text-white'
```

For the complete pattern reference, see `component-patterns.md` section 1.

### 5b. Create `src/lib/theme.ts` — centralized theme constants

This file is the **single source of truth** for all theme tokens used across the app.
Every component, page, and utility imports from here instead of hardcoding values.

```typescript
// src/lib/theme.ts
// ─── Centralized Theme Constants ─────────────────────────────────────────────
// Single source of truth for all theme tokens. Import from here in every
// component — never hardcode hex values or class strings in components.
//
// All values reference CSS variables defined in globals.css.
// Changing a CSS variable automatically updates every usage.

// ── Colors ───────────────────────────────────────────────────────────────────
export const colors = {
  purple: {
    50: 'purple-50',
    100: 'purple-100',
    200: 'purple-200',
    300: 'purple-300',
    400: 'purple-400',
    500: 'purple-500',
    600: 'purple-600',
    700: 'purple-700',
    800: 'purple-800',
    900: 'purple-900',
  },
  indigo: {
    50: 'indigo-50',
    100: 'indigo-100',
    200: 'indigo-200',
    300: 'indigo-300',
    400: 'indigo-400',
    500: 'indigo-500',
    600: 'indigo-600',
    700: 'indigo-700',
    800: 'indigo-800',
    900: 'indigo-900',
  },
  green: {
    50: 'green-50',
    100: 'green-100',
    200: 'green-200',
    300: 'green-300',
    400: 'green-400',
    500: 'green-500',
    600: 'green-600',
    700: 'green-700',
    800: 'green-800',
    900: 'green-900',
  },
  amber: {
    50: 'amber-50',
    100: 'amber-100',
    200: 'amber-200',
    300: 'amber-300',
    400: 'amber-400',
    500: 'amber-500',
    600: 'amber-600',
    700: 'amber-700',
    800: 'amber-800',
    900: 'amber-900',
  },
  red: {
    50: 'red-50',
    100: 'red-100',
    200: 'red-200',
    300: 'red-300',
    400: 'red-400',
    500: 'red-500',
    600: 'red-600',
    700: 'red-700',
    800: 'red-800',
    900: 'red-900',
  },
  gray: {
    50: 'gray-50',
    100: 'gray-100',
    200: 'gray-200',
    300: 'gray-300',
    400: 'gray-400',
    500: 'gray-500',
    600: 'gray-600',
    700: 'gray-700',
    800: 'gray-800',
    900: 'gray-900',
  },
  slate: {
    50: 'slate-50',
    100: 'slate-100',
    200: 'slate-200',
    300: 'slate-300',
    400: 'slate-400',
  },
  white: 'white',
} as const;

// ── Semantic Aliases ─────────────────────────────────────────────────────────
// Map intent to color — change these to re-theme the entire app.
export const semantic = {
  primary: colors.purple[500],
  primaryHover: colors.purple[600],
  primaryLight: colors.purple[400],
  primaryTint: colors.purple[50],

  secondary: colors.indigo[500],
  secondaryHover: colors.indigo[600],

  success: colors.green[500],
  successTint: colors.green[50],

  warning: colors.amber[500],
  warningTint: colors.amber[50],

  destructive: colors.red[500],
  destructiveHover: colors.red[600],
  destructiveTint: colors.red[50],

  textPrimary: colors.gray[800],
  textSecondary: colors.gray[500],
  textDisabled: colors.gray[300],
  textPlaceholder: colors.gray[400],

  bgPage: colors.gray[50],
  bgCard: colors.white,
  bgHover: colors.gray[100],
  bgTableHeader: colors.gray[200],

  border: colors.slate[200],
  borderLight: colors.slate[100],

  ring: colors.purple[500],
} as const;

// ── Component Class Presets ──────────────────────────────────────────────────
// Pre-built class strings for common UI patterns. Use with cn():
//   cn(presets.button.primary, className)
export const presets = {
  button: {
    base: 'inline-flex items-center justify-center rounded font-medium text-base transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 disabled:pointer-events-none disabled:opacity-50',
    primary: 'bg-purple-500 text-white hover:bg-purple-600',
    secondary: 'bg-indigo-500 text-white hover:bg-indigo-600',
    outline: 'border border-slate-200 bg-white text-gray-800 hover:bg-gray-100',
    ghost: 'text-gray-800 hover:bg-gray-100',
    destructive: 'bg-red-500 text-white hover:bg-red-600',
    link: 'text-purple-500 underline-offset-4 hover:underline',
    size: {
      sm: 'h-8 px-3 text-sm',
      md: 'h-[42px] px-4 text-base',
      lg: 'h-12 px-6 text-lg',
    },
  },
  input: {
    base: 'flex w-full rounded border border-slate-200 bg-white text-gray-800 placeholder:text-gray-400 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
    size: {
      sm: 'h-8 px-2.5 text-sm',
      md: 'h-[42px] px-3.5 text-base',
      lg: 'h-12 px-4 text-base',
    },
  },
  card: {
    base: 'rounded bg-white shadow-sm border border-slate-200',
    padded: 'rounded bg-white shadow-sm border border-slate-200 p-6',
  },
  badge: {
    base: 'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium',
    default: 'bg-gray-100 text-gray-500',
    primary: 'bg-purple-50 text-purple-500',
    success: 'bg-green-50 text-green-500',
    warning: 'bg-amber-50 text-amber-500',
    destructive: 'bg-red-50 text-red-500',
  },
  text: {
    heading: 'text-lg font-semibold text-gray-800',
    body: 'text-[15px] text-gray-800',
    secondary: 'text-sm text-gray-500',
    label: 'text-sm font-medium text-gray-700',
  },
  focus: 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500',
} as const;
```

### How to use in components

```typescript
import { cn } from '@/lib/utils';
import { presets, semantic } from '@/lib/theme';

// Use presets with cn() for common patterns
<button className={cn(presets.button.base, presets.button.primary, presets.button.size.md, className)}>

// Use semantic aliases for one-off styling
<div className={cn(`bg-${semantic.primaryTint}`, className)}>

// Import presets for component variants
const variants = {
  primary: presets.button.primary,
  destructive: presets.button.destructive,
};
```

---

## Step 6 — Initialize shadcn/ui

```bash
cd frontend
yarn dlx shadcn@latest init
```

When prompted, select:
- **Style**: New York
- **Base color**: Neutral
- **CSS variables**: Yes
- **Tailwind CSS config**: (use default path)
- **Components directory**: `src/components/ui`
- **Utils directory**: `src/lib`
- **React Server Components**: Yes (we mark client components manually)

If `components.json` already exists, skip this step.

### Verify `components.json`

After init, ensure `frontend/components.json` contains:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

---

## Step 7 — Verify setup

Run these checks to confirm everything is working:

```bash
# 1. Tailwind processes CSS
cd frontend && yarn build 2>&1 | tail -5

# 2. cn() utility exists
ls src/lib/utils.ts

# 3. Theme constants exist
ls src/lib/theme.ts

# 4. components.json exists
ls components.json

# 5. CSS variables are in globals.css
grep -- '--purple_500' src/app/globals.css
```

---

## Step 8 — Install a test primitive

Install the `button` primitive to verify the full pipeline:

```bash
cd frontend && yarn dlx shadcn@latest add button
```

Check the generated file:
```bash
cat frontend/src/components/ui/button.tsx
```

It should:
- Import from `@/lib/utils`
- Use `cva` for variants
- Use CSS variable palette classes (`bg-purple-500`, etc.)
- Export `Button` and `buttonVariants`

---

## Coexistence with MUI

This setup allows MUI and shadcn/Tailwind to coexist:

| Layer | Library | When to use |
|-------|---------|-------------|
| Existing components | MUI + `sx` prop | Maintain existing code, don't migrate unless needed |
| New shared components | shadcn + Tailwind | All new components created via `/create-component` |
| Theme tokens | CSS variables | Shared between both — MUI reads from `theme.ts`, Tailwind reads from CSS vars |
| Icons | `lucide-react` | Both MUI and shadcn components use Lucide |

### Rules for coexistence:
1. **Never mix** MUI `sx` prop and Tailwind classes on the same element
2. **New pages** can use a mix of MUI components (existing) and shadcn components (new)
3. **Existing shared components** (`CustomButton`, `TextInput`, `FormComponent`) remain MUI-based
4. **New shared components** are shadcn-based and go in `src/components/shared/`
5. **Theme colors stay in sync** — CSS variables in `globals.css` match values in `src/utils/theme.ts`

---

## Troubleshooting

### Tailwind classes not applying
- Ensure `@import 'tailwindcss'` is at the top of `globals.css`
- Check that `postcss.config.mjs` uses `@tailwindcss/postcss`
- Restart the dev server after config changes

### CSS variable conflicts
- CSS variables use direct hex values (`--purple_500: #8b5cf6`) — no HSL conversion
- Tailwind config references them as `var(--purple_500)`
- If colors look wrong, verify hex values in the `:root` block of `globals.css`

### Type errors with cn()
- Ensure `clsx` and `tailwind-merge` are installed
- Check import path: `import { cn } from '@/lib/utils'`

### shadcn components not rendering
- Ensure `'use client'` directive is present on interactive components
- Check that `components.json` aliases match your tsconfig paths

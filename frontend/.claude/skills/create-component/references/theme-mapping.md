# Theme Token Mapping — MUI to Tailwind (Flat Palette)

Maps every MUI theme value from `src/utils/theme.ts` to its CSS variable and Tailwind class.
Uses the **flat hex-based palette** approach — same structure as the tone-test project.

**Single source of truth**: All colors come from CSS variables in `globals.css`.
Tailwind classes reference those variables via `tailwind.config.ts`.

---

## Color Palette

### Purple (Primary)

| MUI Theme Path                 | Hex       | CSS Variable   | Tailwind Class                     |
| ------------------------------ | --------- | -------------- | ---------------------------------- |
| `palette.primary.light`        | `#a78bfa` | `--purple_400` | `bg-purple-400`, `text-purple-400` |
| `palette.primary.main`         | `#8b5cf6` | `--purple_500` | `bg-purple-500`, `text-purple-500` |
| `palette.primary.dark`         | `#7c3aed` | `--purple_600` | `bg-purple-600`, `text-purple-600` |
| `palette.primary.contrastText` | `#ffffff` | `--white`      | `text-white`                       |
| (tint)                         | `#f5f3ff` | `--purple_50`  | `bg-purple-50`                     |
| (tint)                         | `#ede9fe` | `--purple_100` | `bg-purple-100`                    |
| (tint)                         | `#ddd6fe` | `--purple_200` | `bg-purple-200`                    |
| (shade)                        | `#6d28d9` | `--purple_700` | `bg-purple-700`                    |
| (shade)                        | `#5b21b6` | `--purple_800` | `bg-purple-800`                    |
| (shade)                        | `#4c1d95` | `--purple_900` | `bg-purple-900`                    |

**Usage**: Primary buttons, active tab indicators, focus rings, links.

### Indigo (Secondary)

| MUI Theme Path            | Hex       | CSS Variable   | Tailwind Class                     |
| ------------------------- | --------- | -------------- | ---------------------------------- |
| `palette.secondary.light` | `#818cf8` | `--indigo_400` | `bg-indigo-400`, `text-indigo-400` |
| `palette.secondary.main`  | `#6366f1` | `--indigo_500` | `bg-indigo-500`, `text-indigo-500` |
| `palette.secondary.dark`  | `#4f46e5` | `--indigo_600` | `bg-indigo-600`, `text-indigo-600` |
| (tint)                    | `#eef2ff` | `--indigo_50`  | `bg-indigo-50`                     |
| (tint)                    | `#e0e7ff` | `--indigo_100` | `bg-indigo-100`                    |

**Usage**: Secondary actions, badges, chart accents.

### Green (Success)

| MUI Theme Path          | Hex       | CSS Variable  | Tailwind Class                   |
| ----------------------- | --------- | ------------- | -------------------------------- |
| `palette.success.light` | `#34d399` | `--green_400` | `bg-green-400`, `text-green-400` |
| `palette.success.main`  | `#10b981` | `--green_500` | `bg-green-500`, `text-green-500` |
| `palette.success.dark`  | `#059669` | `--green_600` | `bg-green-600`, `text-green-600` |
| (tint)                  | `#ecfdf5` | `--green_50`  | `bg-green-50`                    |
| (tint)                  | `#d1fae5` | `--green_100` | `bg-green-100`                   |

**Usage**: Success notifications, active status, online indicators.

### Amber (Warning)

| MUI Theme Path          | Hex       | CSS Variable  | Tailwind Class                   |
| ----------------------- | --------- | ------------- | -------------------------------- |
| `palette.warning.light` | `#fbbf24` | `--amber_400` | `bg-amber-400`, `text-amber-400` |
| `palette.warning.main`  | `#f59e0b` | `--amber_500` | `bg-amber-500`, `text-amber-500` |
| `palette.warning.dark`  | `#d97706` | `--amber_600` | `bg-amber-600`, `text-amber-600` |
| (tint)                  | `#fffbeb` | `--amber_50`  | `bg-amber-50`                    |
| (tint)                  | `#fef3c7` | `--amber_100` | `bg-amber-100`                   |

**Usage**: Warning notifications, pending status, attention badges.

### Red (Error / Destructive)

| MUI Theme Path        | Hex       | CSS Variable | Tailwind Class               |
| --------------------- | --------- | ------------ | ---------------------------- |
| `palette.error.light` | `#f87171` | `--red_400`  | `bg-red-400`, `text-red-400` |
| `palette.error.main`  | `#ef4444` | `--red_500`  | `bg-red-500`, `text-red-500` |
| `palette.error.dark`  | `#dc2626` | `--red_600`  | `bg-red-600`, `text-red-600` |
| (tint)                | `#fef2f2` | `--red_50`   | `bg-red-50`                  |
| (tint)                | `#fee2e2` | `--red_100`  | `bg-red-100`                 |

**Usage**: Error states, destructive actions, delete buttons, validation errors.

### Gray (Text, Backgrounds)

| MUI Theme Path               | Hex       | CSS Variable | Tailwind Class  |
| ---------------------------- | --------- | ------------ | --------------- |
| `palette.background.default` | `#f9fafb` | `--gray_50`  | `bg-gray-50`    |
| (light bg)                   | `#f3f4f6` | `--gray_100` | `bg-gray-100`   |
| (table header)               | `#e5e7eb` | `--gray_200` | `bg-gray-200`   |
| `palette.text.disabled`      | `#d1d5db` | `--gray_300` | `text-gray-300` |
| (placeholder)                | `#9ca3af` | `--gray_400` | `text-gray-400` |
| `palette.text.secondary`     | `#6b7280` | `--gray_500` | `text-gray-500` |
| (subtle label)               | `#4b5563` | `--gray_600` | `text-gray-600` |
| (strong label)               | `#374151` | `--gray_700` | `text-gray-700` |
| `palette.text.primary`       | `#1f2937` | `--gray_800` | `text-gray-800` |
| (darkest)                    | `#111827` | `--gray_900` | `text-gray-900` |

### Slate (Borders, Dividers)

| MUI Theme Path    | Hex       | CSS Variable  | Tailwind Class     |
| ----------------- | --------- | ------------- | ------------------ |
| `palette.divider` | `#e2e8f0` | `--slate_200` | `border-slate-200` |
| (subtle border)   | `#cbd5e1` | `--slate_300` | `border-slate-300` |
| (icon muted)      | `#94a3b8` | `--slate_400` | `text-slate-400`   |

### White

| MUI Theme Path                 | Hex       | CSS Variable | Tailwind Class |
| ------------------------------ | --------- | ------------ | -------------- |
| `palette.background.paper`     | `#ffffff` | `--white`    | `bg-white`     |
| `palette.primary.contrastText` | `#ffffff` | `--white`    | `text-white`   |

---

## Semantic Shortcuts

For convenience, use these common color assignments:

| Purpose           | Tailwind Class        | CSS Variable   |
| ----------------- | --------------------- | -------------- |
| Primary action    | `bg-purple-500`       | `--purple_500` |
| Primary hover     | `hover:bg-purple-600` | `--purple_600` |
| Primary text/link | `text-purple-500`     | `--purple_500` |
| Primary tint bg   | `bg-purple-50`        | `--purple_50`  |
| Error/destructive | `bg-red-500`          | `--red_500`    |
| Error hover       | `hover:bg-red-600`    | `--red_600`    |
| Success           | `bg-green-500`        | `--green_500`  |
| Warning           | `bg-amber-500`        | `--amber_500`  |
| Page background   | `bg-gray-50`          | `--gray_50`    |
| Card background   | `bg-white`            | `--white`      |
| Primary text      | `text-gray-800`       | `--gray_800`   |
| Secondary text    | `text-gray-500`       | `--gray_500`   |
| Disabled text     | `text-gray-300`       | `--gray_300`   |
| Border/divider    | `border-slate-200`    | `--slate_200`  |
| Focus ring        | `ring-purple-500`     | `--purple_500` |

---

## Typography Tokens

### Font Family

MUI: `'"Inter", "Roobert", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'`

Tailwind: The font is set globally via `next/font/google` in `layout.tsx`. Use `font-sans` or `font-inter`.

### Font Sizes

| MUI Custom Token                  | Value              | Tailwind Class | Usage                        |
| --------------------------------- | ------------------ | -------------- | ---------------------------- |
| `custom.typography.fontSize.xs`   | `0.75rem` (12px)   | `text-xs`      | Small labels, captions       |
| `custom.typography.fontSize.sm`   | `0.8125rem` (13px) | `text-sm`      | Secondary text, descriptions |
| `custom.typography.fontSize.base` | `0.875rem` (14px)  | `text-base`    | Default body text, buttons   |
| `custom.typography.fontSize.lg`   | `1rem` (16px)      | `text-lg`      | Emphasized text              |
| `custom.typography.fontSize.xl`   | `1.125rem` (18px)  | `text-xl`      | Sub-headings                 |

| MUI Typography Variant | Size       | Weight | Tailwind Equivalent          |
| ---------------------- | ---------- | ------ | ---------------------------- |
| `h1`                   | `2.25rem`  | 700    | `text-4xl font-bold`         |
| `h2`                   | `1.875rem` | 600    | `text-3xl font-semibold`     |
| `h3`                   | `1.5rem`   | 600    | `text-2xl font-semibold`     |
| `h4`                   | `1.25rem`  | 600    | `text-xl font-semibold`      |
| `h5`                   | `1.125rem` | 600    | `text-lg font-semibold`      |
| `h6`                   | `1rem`     | 600    | `text-base font-semibold`    |
| `body1`                | `15px`     | 400    | `text-[15px] font-normal`    |
| `body2`                | `14px`     | 400    | `text-base font-normal`      |
| `button`               | —          | 500    | `font-medium` (no uppercase) |

### Font Weights

| MUI Custom Token                        | Value | Tailwind Class  |
| --------------------------------------- | ----- | --------------- |
| `custom.typography.fontWeight.normal`   | 400   | `font-normal`   |
| `custom.typography.fontWeight.medium`   | 500   | `font-medium`   |
| `custom.typography.fontWeight.semibold` | 600   | `font-semibold` |
| `custom.typography.fontWeight.bold`     | 700   | `font-bold`     |

---

## Shadow Tokens

| CSS Variable  | Value                                   | Tailwind Class | Usage                                  |
| ------------- | --------------------------------------- | -------------- | -------------------------------------- |
| `--shadow-xs` | `0 1px 2px 0 rgba(16,24,40,0.05)`       | `shadow-xs`    | Subtle elevation, inputs               |
| `--shadow-sm` | `0 1px 3px 0 rgba(0,0,0,0.1)`           | `shadow-sm`    | Cards (MUI MuiCard)                    |
| `--shadow-md` | `0 4px 6px -1px rgba(0,0,0,0.1), ...`   | `shadow-md`    | Elevated panels (MUI Paper elevation2) |
| `--shadow-lg` | `0 10px 15px -3px rgba(0,0,0,0.1), ...` | `shadow-lg`    | Dialogs, dropdowns                     |

---

## Border Radius Tokens

| CSS Variable   | Value  | Tailwind Class           | MUI Equivalent                         |
| -------------- | ------ | ------------------------ | -------------------------------------- |
| `--radius-xs`  | `2px`  | `rounded-xs`             | —                                      |
| `--radius-sm`  | `4px`  | `rounded-sm`             | `custom.borderRadius.sm`               |
| `--radius-md`  | `5px`  | `rounded` / `rounded-md` | `shape.borderRadius` (project default) |
| `--radius-lg`  | `8px`  | `rounded-lg`             | —                                      |
| `--radius-xl`  | `10px` | `rounded-xl`             | —                                      |
| `--radius-2xl` | `12px` | `rounded-2xl`            | —                                      |

**Note**: The project default is 5px (`--radius-md`). Use `rounded` or `rounded-md` for standard UI elements.

---

## Spacing Tokens

| CSS Variable  | Value  | Tailwind Class     | Common Usage                 |
| ------------- | ------ | ------------------ | ---------------------------- |
| `--space-xs`  | `2px`  | `p-0.5`, `gap-0.5` | Tight spacing                |
| `--space-sm`  | `4px`  | `p-1`, `gap-1`     | Icon gaps                    |
| `--space-lg`  | `8px`  | `p-2`, `gap-2`     | Button padding, standard gap |
| `--space-4xl` | `16px` | `p-4`, `gap-4`     | Section padding              |
| `--space-6xl` | `20px` | `p-5`, `gap-5`     | Card padding                 |
| `--space-7xl` | `24px` | `p-6`, `gap-6`     | Content padding              |
| `--space-8xl` | `32px` | `p-8`, `gap-8`     | Page-level spacing           |

### Component Sizing

| Purpose          | MUI Value  | Tailwind Class  |
| ---------------- | ---------- | --------------- |
| Button height    | `42px`     | `h-[42px]`      |
| Button padding   | `8px 16px` | `py-2 px-4`     |
| Tab min-height   | `44px`     | `min-h-[44px]`  |
| Dialog min-width | `450px`    | `min-w-[450px]` |
| Sidebar width    | `200px`    | `w-[200px]`     |

---

## Component-Specific Class Recipes

### Button (matching MUI MuiButton)

```
rounded py-2 px-4 font-medium text-base shadow-none hover:shadow-none
```

### Paper / Card (matching MUI MuiPaper/MuiCard)

```
rounded shadow-sm bg-white
```

### TextField / Input (matching MUI MuiTextField)

```
rounded border border-slate-200 bg-white
```

### Dialog (matching MUI MuiDialog)

```
rounded bg-white
```

### Tab (matching MUI MuiTab)

```
min-h-[44px] font-medium
Selected: text-purple-500 border-b-2 border-purple-500
```

### Chip (matching MUI MuiChip)

```
rounded text-sm
```

### DataGrid Header (matching existing pattern)

```
bg-gray-200 font-semibold uppercase text-xs text-gray-600
```

---

## Focus & Interaction States

| State           | Tailwind Equivalent                                                             |
| --------------- | ------------------------------------------------------------------------------- |
| Focus ring      | `focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none` |
| Disabled        | `disabled:opacity-50 disabled:pointer-events-none`                              |
| Hover (primary) | `hover:bg-purple-600`                                                           |
| Hover (default) | `hover:bg-gray-50`                                                              |
| Active/pressed  | `active:scale-[0.98]` (subtle)                                                  |

---

## Quick Reference Card

Copy-paste these common class combinations:

```
// Primary button
"bg-purple-500 text-white hover:bg-purple-600 rounded h-[42px] px-4 font-medium text-base"

// Secondary/outline button
"border border-slate-200 bg-white text-gray-800 hover:bg-gray-100 rounded h-[42px] px-4 font-medium text-base"

// Danger button
"bg-red-500 text-white hover:bg-red-600 rounded h-[42px] px-4 font-medium text-base"

// Ghost button
"text-gray-800 hover:bg-gray-100 rounded h-[42px] px-4 font-medium text-base"

// Text input
"rounded border border-slate-200 bg-white px-3 py-2 text-base text-gray-800 placeholder:text-gray-400 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none"

// Card container
"rounded bg-white shadow-sm border border-slate-200 p-6"

// Section header text
"text-lg font-semibold text-gray-800"

// Body text
"text-[15px] text-gray-800"

// Secondary/helper text
"text-sm text-gray-500"

// Badge/chip
"rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500"

// Success badge
"rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-500"

// Error badge
"rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-500"

// Table header cell
"bg-gray-200 px-4 py-2 text-xs font-semibold uppercase text-gray-600"

// Divider line
"border-t border-slate-200"

// Icon in button
"h-4 w-4 mr-2"
```

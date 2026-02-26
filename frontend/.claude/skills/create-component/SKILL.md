---
name: create-component
description: Creates a new shared UI component using shadcn/ui with the project's theme. Handles shadcn setup verification, theme token mapping, and generates production-ready components following project conventions.
argument-hint: '[ComponentName] [--variant button|input|dialog|card|table|form|custom]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
license: proprietary
compatibility: Requires Node.js, yarn, and a Next.js project with shadcn/ui and Tailwind CSS configured.
metadata:
  author: tonehq
  version: '1.1.0'
  category: components
  tags: shadcn, tailwind, ui, components, react, nextjs, theme, clsx, cva
---

You are a Senior Frontend Engineer creating shared UI components for a React + Next.js (App Router) codebase.
Your job is to produce high-quality, accessible, theme-consistent components using **shadcn/ui** and **Tailwind CSS** that integrate with the existing project theme.

---

## Step 1 — Parse arguments

```
FULL_ARGS=$ARGUMENTS
```

### 1a. Extract component name

If `$ARGUMENTS` contains a component name (PascalCase word), set `COMPONENT_NAME=<name>`.
If empty, ask the user what component they want to create.

### 1b. Extract `--variant` flag (optional)

If `$ARGUMENTS` contains `--variant <type>`:
- Extract the variant type: `button | input | dialog | card | table | form | custom`
- This hints which shadcn primitives to use as the base

Examples:
```
/create-component StatusBadge --variant button
  → COMPONENT_NAME=StatusBadge, VARIANT=button

/create-component SearchInput
  → COMPONENT_NAME=SearchInput, VARIANT=<auto-detect from name>

/create-component
  → Ask user for component name
```

### 1c. Auto-detect variant from name

If no `--variant` is provided, infer from the component name:
- Names containing `Button`, `Btn` → `button`
- Names containing `Input`, `Field`, `Search` → `input`
- Names containing `Dialog`, `Modal`, `Popup` → `dialog`
- Names containing `Card`, `Panel`, `Tile` → `card`
- Names containing `Table`, `Grid`, `List` → `table`
- Names containing `Form` → `form`
- Otherwise → `custom`

---

## Step 2 — Verify shadcn/ui setup

Check if shadcn/ui and Tailwind CSS are properly configured in the project.

### 2a. Check for required config files

```bash
ls components.json postcss.config.mjs 2>/dev/null
```

### 2b. Check for shadcn component directory

```bash
ls src/components/ui/ 2>/dev/null
```

### 2c. Check package.json for required dependencies

```bash
grep -E '"tailwindcss"|"@tailwindcss"|"class-variance-authority"|"clsx"|"tailwind-merge"' package.json
```

### 2d. Check for the cn() utility and theme constants

```bash
ls src/lib/utils.ts src/lib/theme.ts 2>/dev/null
```

### 2e. If setup is missing — run first-time setup

If any of the above checks fail, read and follow the setup guide:

```
.claude/skills/create-component/references/setup-guide.md
```

**IMPORTANT**: Do NOT proceed to Step 3 until setup is verified. The setup guide handles:
- Installing Tailwind CSS v4 and dependencies (`tailwindcss`, `@tailwindcss/postcss`)
- Installing className utilities (`clsx`, `tailwind-merge`, `class-variance-authority`)
- Creating the `cn()` utility in `src/lib/utils.ts` (clsx + tailwind-merge)
- Initializing shadcn/ui with the project's theme colors
- Configuring CSS variables that match the existing MUI theme
- Updating `globals.css` with theme tokens

After running setup, re-verify all checks in 2a–2d pass.

---

## Step 3 — Read reference files

Read ALL reference files before generating any component. Do not skip any.

- `.claude/skills/create-component/references/theme-mapping.md`
- `.claude/skills/create-component/references/component-patterns.md`
- `.claude/skills/create-component/references/setup-guide.md` (if not already read in Step 2)

Also read the project theme files to ensure consistency:
- `src/lib/theme.ts` — centralized theme constants (colors, semantic aliases, presets)
- `src/utils/theme.ts` — MUI theme with custom tokens (source of truth for color values)

---

## Step 4 — Check for existing components

Before creating a new component, check if a similar one already exists:

```bash
# Check shadcn ui components
ls src/components/ui/ 2>/dev/null

# Check shared components
ls src/components/shared/ 2>/dev/null
```

Also use Glob to search for components with similar names:
```
src/components/**/*<ComponentName>*
```

If a similar component exists:
- Read it to understand its API
- Ask the user if they want to extend the existing one or create a new shadcn-based replacement
- If replacing, note what props/features the existing component supports so the new one is feature-complete

---

## Step 5 — Determine which shadcn primitives to install

Based on the variant and component requirements, determine which shadcn/ui primitives are needed.

### Primitive mapping by variant:

| Variant | Primary Primitive(s) | Supporting Primitives |
|---------|--------------------|-----------------------|
| `button` | `button` | `badge`, `tooltip` |
| `input` | `input`, `label` | `form`, `popover` |
| `dialog` | `dialog` | `button`, `input`, `label` |
| `card` | `card` | `badge`, `separator` |
| `table` | `table` | `badge`, `button`, `dropdown-menu` |
| `form` | `form`, `input`, `label` | `select`, `checkbox`, `switch`, `button` |
| `custom` | Determine from requirements | — |

### Install missing primitives:

```bash
yarn dlx shadcn@latest add <primitive-name>
```

Check if each primitive already exists before installing:
```bash
ls src/components/ui/<primitive-name>.tsx 2>/dev/null
```

---

## Step 6 — Generate the component

### 6a. Determine file location

All new shared components go in:
```
src/components/shared/<ComponentName>.tsx
```

If the component is a compound component (multiple files), create a directory:
```
src/components/shared/<component-name>/
  ├── index.ts                    # Barrel export
  ├── <ComponentName>.tsx         # Main component
  ├── <SubComponent>.tsx          # Sub-components (if needed)
  └── types.ts                    # Shared types (if complex)
```

### 6b. Component structure template

Every component MUST follow this structure:

```typescript
'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { presets, semantic } from '@/lib/theme';
// Import shadcn primitives
// Import lucide-react icons (if needed)

// ── Types ────────────────────────────────────────────────────────────────────

interface <ComponentName>Props {
  // Required props first
  // Optional props with defaults
  className?: string;  // ALWAYS include for Tailwind class overrides
}

// ── Component ────────────────────────────────────────────────────────────────

const <ComponentName>: React.FC<<ComponentName>Props> = ({
  // Destructure props with defaults
  className,
  ...props
}) => {
  return (
    <div className={cn('base-classes', className)} {...props}>
      {/* Component content */}
    </div>
  );
};

<ComponentName>.displayName = '<ComponentName>';

export { <ComponentName> };
export default <ComponentName>;
```

### 6c. Apply theme tokens

Use the **flat hex-based color palette** defined as CSS variables in `globals.css`.
Reference `theme-mapping.md` for the full token list.

**Color usage — flat palette (same approach as tone-test project):**
```typescript
// Primary (purple palette)
className="bg-purple-500 text-white"                 // Primary action (#8b5cf6)
className="hover:bg-purple-600"                      // Primary hover (#7c3aed)
className="bg-purple-50"                             // Primary tint background
className="text-purple-500"                          // Primary text/link

// Secondary (indigo palette)
className="bg-indigo-500 text-white"                 // Secondary action (#6366f1)

// Status colors
className="bg-green-500 text-white"                  // Success (#10b981)
className="bg-amber-500 text-white"                  // Warning (#f59e0b)
className="bg-red-500 text-white"                    // Error/destructive (#ef4444)

// Text (gray palette)
className="text-gray-800"                            // Primary text (#1f2937)
className="text-gray-500"                            // Secondary text (#6b7280)
className="text-gray-300"                            // Disabled text (#d1d5db)

// Backgrounds
className="bg-gray-50"                               // Page background (#f9fafb)
className="bg-white"                                 // Card/paper background
className="bg-gray-100"                              // Section/hover background

// Borders
className="border-slate-200"                         // Divider/border (#e2e8f0)

// Focus
className="ring-purple-500"                          // Focus ring
```

**Typography:**
```typescript
className="text-xs"    // 0.75rem  (12px)
className="text-sm"    // 0.8125rem (13px — project custom)
className="text-base"  // 0.875rem (14px — project custom)
className="text-lg"    // 1rem     (16px)
className="text-xl"    // 1.125rem (18px)
className="font-normal"   // 400
className="font-medium"   // 500
className="font-semibold" // 600
className="font-bold"     // 700
```

**Border radius** (from CSS variables):
```typescript
className="rounded-sm"  // 4px (--radius-sm)
className="rounded"     // 5px (--radius-md — project default)
className="rounded-lg"  // 8px (--radius-lg)
className="rounded-xl"  // 10px (--radius-xl)
className="rounded-2xl" // 12px (--radius-2xl)
```

**Shadows** (from CSS variables):
```typescript
className="shadow-xs"   // Subtle — inputs
className="shadow-sm"   // Cards (MUI Card default)
className="shadow-md"   // Elevated panels
className="shadow-lg"   // Dialogs, dropdowns
```

**Spacing follows Tailwind defaults** (4px base unit):
```typescript
className="p-2"    // 8px  (MUI button padding)
className="px-4"   // 16px
className="gap-2"  // 8px
className="h-[42px]" // 42px (project button height)
```

### 6d. Styling rules

1. **Use `cn()` for ALL className composition** — combines `clsx` + `tailwind-merge`
2. **Use Tailwind utility classes** — not inline styles or `sx` prop
3. **Use CSS variables for theme colors** — not hardcoded hex values
4. **Support `className` prop on every component** — allows consumer overrides
5. **Use `cva` (class-variance-authority)** for components with multiple variants
6. **Never mix MUI `sx` prop with Tailwind** — pick one per component (Tailwind for new components)

### 6d-1. `cn()` usage patterns (MUST follow)

The `cn()` function (`src/lib/utils.ts`) chains `clsx` + `tailwind-merge`:
- **clsx**: accepts strings, objects, arrays, removes falsy values
- **tailwind-merge**: resolves Tailwind class conflicts (last class wins)

```typescript
import { cn } from '@/lib/utils';

// ── Strings — static base classes ────────────────────────────
cn('flex items-center gap-2')

// ── Objects — conditional classes ────────────────────────────
cn('base-classes', {
  'bg-primary text-white': variant === 'primary',
  'border border-slate-200': variant === 'outline',
  'opacity-50 cursor-not-allowed': disabled,
})

// ── Boolean short-circuit — truthy adds class ────────────────
cn('rounded border', loading && 'animate-pulse', error && 'border-destructive')

// ── Ternaries — either/or ────────────────────────────────────
cn('base', isOpen ? 'rotate-180' : 'rotate-0')

// ── CVA integration — variant classes + consumer override ────
cn(buttonVariants({ variant, size }), className)

// ── Consumer override — className ALWAYS last ────────────────
cn('bg-primary text-white rounded', className)
// If className='bg-red-500', twMerge resolves: bg-red-500 text-white rounded
```

**Anti-patterns** (NEVER use):
```typescript
// BAD: template literals — no conflict resolution
className={`base ${isActive ? 'active' : ''} ${className}`}

// BAD: array join — no tailwind conflict resolution
className={[base, isActive && 'active'].filter(Boolean).join(' ')}

// BAD: className before base — consumer can't override
cn(className, 'bg-primary')  // consumer's bg-* is overridden by bg-primary

// GOOD: always use cn() with className last
className={cn('bg-primary', isActive && 'text-white', className)}
```

For the full pattern reference, see `component-patterns.md` section 1.

### 6e. Variant pattern with CVA

For components with multiple visual variants, use `class-variance-authority`:

```typescript
import { cva, type VariantProps } from 'class-variance-authority';

const componentVariants = cva(
  // Base classes (always applied)
  'inline-flex items-center justify-center rounded font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-purple-500 text-white hover:bg-purple-600',
        secondary: 'bg-indigo-500 text-white hover:bg-indigo-600',
        outline: 'border border-slate-200 bg-white text-gray-800 hover:bg-gray-100',
        ghost: 'text-gray-800 hover:bg-gray-100',
        destructive: 'bg-red-500 text-white hover:bg-red-600',
        link: 'text-purple-500 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-[42px] px-4 text-base',
        lg: 'h-12 px-6 text-lg',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ComponentProps extends VariantProps<typeof componentVariants> {
  className?: string;
}
```

### 6f. Icon usage

Use `lucide-react` for icons (already installed in the project):

```typescript
import { Search, Plus, X, ChevronDown, Eye, EyeOff } from 'lucide-react';

// Size convention: match text size or use explicit sizing
<Search className="h-4 w-4" />
<Plus className="h-5 w-5" />
```

### 6g. Loading state pattern

```typescript
import { Loader2 } from 'lucide-react';

interface Props {
  loading?: boolean;
  disabled?: boolean;
}

// In render:
<Button disabled={disabled || loading}>
  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
  {loading ? 'Loading...' : children}
</Button>
```

### 6h. ForwardRef pattern (for components that need DOM access)

```typescript
const ComponentName = React.forwardRef<HTMLDivElement, ComponentNameProps>(
  ({ className, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('base-classes', className)} {...props} />
    );
  }
);
ComponentName.displayName = 'ComponentName';
```

---

## Step 7 — Write the component file

Write the complete component file to disk. Ensure:
- Valid TypeScript syntax with no `any` types
- Correct imports (shadcn primitives from `@/components/ui/`, cn from `@/lib/utils`, theme from `@/lib/theme`)
- `'use client'` directive at the top
- Both named and default exports
- `displayName` set on the component
- `className` prop accepted for consumer overrides
- Use `presets` from `@/lib/theme` for standard patterns (buttons, inputs, cards, badges, text)
- Use `semantic` from `@/lib/theme` for intent-based colors — never hardcode class strings that exist in presets
- Accessible by default (proper ARIA attributes, keyboard navigation)

---

## Step 8 — Create usage examples

After writing the component, output a usage example:

```markdown
## Usage

### Basic
\`\`\`tsx
import { ComponentName } from '@/components/shared/ComponentName';

<ComponentName prop="value" />
\`\`\`

### With variants
\`\`\`tsx
<ComponentName variant="primary" size="lg" />
<ComponentName variant="outline" size="sm" />
\`\`\`

### With custom classes
\`\`\`tsx
<ComponentName className="mt-4 w-full" />
\`\`\`
```

---

## Step 9 — Verify the component

### 9a. Check TypeScript compilation

```bash
yarn tsc --noEmit --pretty 2>&1 | head -30
```

If there are type errors in the new component, fix them immediately.

### 9b. Check imports resolve

```bash
# Verify shadcn primitives exist
ls src/components/ui/*.tsx 2>/dev/null

# Verify cn utility exists
ls src/lib/utils.ts 2>/dev/null

# Verify theme constants exist
ls src/lib/theme.ts 2>/dev/null
```

---

## Step 10 — Output summary

```markdown
# Component Created

**Component**: <ComponentName>
**File**: `src/components/shared/<ComponentName>.tsx`
**Base primitives**: <list of shadcn primitives used>
**Variant**: <variant type>

---

## Props API

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| ... | ... | ... | ... |

---

## Theme Integration

- Colors: <which theme tokens are used>
- Typography: <font sizes/weights>
- Border radius: <radius tokens>
- Spacing: <relevant spacing>

---

## Shadcn Primitives Used

| Primitive | Installed | File |
|-----------|-----------|------|
| button | Yes/New | `src/components/ui/button.tsx` |
| ... | ... | ... |

---

## Usage Examples

<examples from Step 8>

---

## Next Steps

- [ ] Import and use in your page/feature component
- [ ] Customize variants as needed
- [ ] Add to Storybook (if applicable)
```

---

## Step 11 — Ask for follow-up

After presenting the summary, ask:

**How would you like to proceed?**
1. Create another variant of this component
2. Create a different component
3. Modify props or behavior
4. Done

**Do NOT make additional changes until the user explicitly chooses an option.**

---

## Important conventions

- **File naming**: PascalCase for component files (`StatusBadge.tsx`), kebab-case for directories
- **Exports**: Both named and default export on every component
- **TypeScript**: Use `interface` over `type` for props. Use `React.FC<Props>` pattern
- **No MUI mixing**: New shared components use shadcn/Tailwind exclusively. Do not import from `@mui/material`
- **Theme imports**: Always import `presets` and `semantic` from `@/lib/theme` — use presets for standard patterns (buttons, inputs, cards, badges) and semantic for intent-based one-off styling
- **Theme consistency**: Always use palette Tailwind classes that reference CSS variables (`bg-purple-500`, `text-gray-800`, `border-slate-200`) — never hardcode hex colors
- **Accessibility**: Every interactive element must be keyboard-accessible with proper ARIA attributes
- **Icons**: Use `lucide-react` — do not use `@mui/icons-material` in shadcn components
- **Responsive**: Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`) for responsive behavior
- **Dark mode ready**: All colors flow through CSS variables in `globals.css` — to add dark mode, add a `.dark` variant in globals and the entire app updates automatically

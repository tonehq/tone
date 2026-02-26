# Component Patterns Reference

Production-ready patterns for building shadcn/ui components with Tailwind CSS.
Based on proven patterns from real-world React projects. Every new component
created by `/create-component` MUST follow these patterns.

---

## 1. The `cn()` Utility — className Composition

The `cn()` function is the backbone of all className handling. It combines
**clsx** (conditional class composition) with **tailwind-merge** (conflict
resolution).

### Implementation

```typescript
// src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### How it works

1. **clsx** accepts strings, objects, arrays, and falsy values — returns a single
   class string with falsy values removed
2. **tailwind-merge** resolves Tailwind class conflicts so the last class wins
   (e.g., `cn('px-4', 'px-2')` → `'px-2'`)

### Usage patterns

#### Strings — static base classes

```typescript
cn('flex items-center gap-2')
// → 'flex items-center gap-2'
```

#### Objects — conditional classes

```typescript
cn('base-classes', {
  'bg-primary text-white': variant === 'primary',
  'bg-transparent border': variant === 'outline',
  'opacity-50 cursor-not-allowed': disabled,
})
// Only truthy keys are included
```

#### Arrays — grouped conditionals

```typescript
cn([
  'flex items-center',
  isActive && 'bg-primary',
  isDisabled && 'opacity-50',
])
// Falsy values (false, undefined, null, 0, '') are stripped
```

#### Inline ternaries — either/or classes

```typescript
cn(
  'base-classes',
  isOpen ? 'rotate-180' : 'rotate-0',
  size === 'lg' ? 'h-12 px-6' : 'h-9 px-3',
)
```

#### Boolean short-circuit — add class when truthy

```typescript
cn(
  'rounded border',
  loading && 'animate-pulse',
  error && 'border-destructive',
  !error && 'border-input',
)
```

#### Consumer override — always last

```typescript
// className prop is ALWAYS the last argument so consumers can override
cn('bg-primary text-white rounded px-4', className)
// If className='bg-red-500', tailwind-merge resolves bg-primary vs bg-red-500 → bg-red-500
```

#### Nested cn — composing sub-component classes

```typescript
cn(
  'flex items-center',
  variantType && buttonVariants({ variantType }),
  buttonVariants({ size, shape }),
  className,
)
```

### Why tailwind-merge matters

Without `twMerge`, conflicting classes stack:
```
clsx('bg-primary', 'bg-red-500') → 'bg-primary bg-red-500'  // BOTH applied — unpredictable
twMerge(clsx('bg-primary', 'bg-red-500')) → 'bg-red-500'    // Last wins — correct
```

This is critical for the `className` override pattern. Without `twMerge`, consumer
overrides silently fail.

### Anti-patterns

```typescript
// BAD: String concatenation — no conflict resolution, no falsy removal
className={`base ${isActive ? 'active' : ''} ${className}`}

// BAD: Template literal — same problems
className={`${styles.base} ${variant === 'primary' ? styles.primary : ''}`}

// BAD: Array join — no tailwind conflict resolution
className={['base', isActive && 'active', className].filter(Boolean).join(' ')}

// GOOD: Always use cn()
className={cn('base', isActive && 'active', className)}
```

---

## 2. ForwardRef Pattern

All components that render a single DOM element MUST use `forwardRef` so consumers
can access the underlying DOM node.

### Basic forwardRef

```typescript
import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  // Custom props go here
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl bg-white text-gray-800 shadow-sm border border-slate-200',
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = 'Card';

export { Card };
```

### ForwardRef with custom props

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, loading, leftIcon, rightIcon, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center rounded font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500',
        'disabled:pointer-events-none disabled:opacity-50',
        (loading || disabled) && 'opacity-50 cursor-not-allowed',
        className,
      )}
      disabled={loading || disabled}
      {...props}
    >
      {leftIcon && !loading && leftIcon}
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
      {rightIcon && rightIcon}
    </button>
  ),
);
Button.displayName = 'Button';
```

### ForwardRef wrapping Radix UI primitives

```typescript
import { Content, Overlay, Portal } from '@radix-ui/react-dialog';

const DialogContent = React.forwardRef<
  React.ElementRef<typeof Content>,
  React.ComponentPropsWithoutRef<typeof Content> & {
    hideOverlay?: boolean;
  }
>(({ className, children, hideOverlay, ...props }, ref) => (
  <Portal>
    {!hideOverlay && <DialogOverlay />}
    <Content
      ref={ref}
      className={cn(
        'fixed z-50 grid w-full max-w-lg bg-gray-50 p-6 shadow-lg',
        'data-[state=open]:animate-in data-[state=closed]:animate-out',
        'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
        className,
      )}
      {...props}
    >
      {children}
    </Content>
  </Portal>
));
DialogContent.displayName = 'DialogContent';
```

**Key rules:**
- `displayName` is REQUIRED on every forwardRef component (React DevTools)
- For Radix wrappers, use `React.ElementRef<typeof Primitive>` as the ref type
- For Radix wrappers, use `React.ComponentPropsWithoutRef<typeof Primitive>` as the base props type
- Intersect (`&`) custom props after the Radix base type

---

## 3. CVA (Class Variance Authority) Pattern

Use CVA for components with multiple visual variants. CVA provides type-safe
variant management and clean separation of base styles from variant-specific styles.

### Basic CVA

```typescript
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  // Base classes — always applied
  'inline-flex items-center rounded px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-purple-500 text-white',
        secondary: 'bg-indigo-500 text-white',
        destructive: 'bg-red-500 text-white',
        outline: 'border border-slate-200 text-gray-800',
        success: 'bg-green-500 text-white',
        warning: 'bg-amber-500 text-white',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  ),
);
Badge.displayName = 'Badge';

export { Badge, badgeVariants };
```

### Multi-axis CVA

```typescript
const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-purple-500 text-white hover:bg-purple-600',
        secondary: 'bg-indigo-500 text-white hover:bg-indigo-600',
        outline: 'border border-slate-200 bg-white text-gray-800 hover:bg-gray-100',
        ghost: 'text-gray-800 hover:bg-gray-100',
        destructive: 'bg-red-500 text-white hover:bg-red-600',
        link: 'text-purple-500 underline-offset-2 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-sm rounded-sm',
        md: 'h-[42px] px-4 text-base rounded',
        lg: 'h-12 px-6 text-lg rounded',
        icon: 'h-[42px] w-[42px] rounded',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
);
```

### CVA with compound variants

Use `compoundVariants` when specific variant combinations need special styling:

```typescript
const inputVariants = cva(
  'flex w-full items-center border bg-white text-gray-800 placeholder:text-gray-400 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none',
  {
    variants: {
      size: {
        sm: 'h-8 px-2.5 text-sm rounded-sm',
        md: 'h-[42px] px-3.5 text-base rounded',
        lg: 'h-12 px-4 text-base rounded',
      },
      state: {
        default: 'border-slate-200',
        error: 'border-red-500 focus-visible:ring-red-500',
        success: 'border-green-500 focus-visible:ring-green-500',
      },
      disabled: {
        true: 'cursor-not-allowed opacity-50 bg-gray-100',
        false: 'cursor-text',
      },
    },
    compoundVariants: [
      // When disabled, override error/success border back to neutral
      { disabled: true, state: 'error', className: 'border-slate-200' },
      { disabled: true, state: 'success', className: 'border-slate-200' },
    ],
    defaultVariants: {
      size: 'md',
      state: 'default',
      disabled: false,
    },
  },
);
```

**Key rules:**
- Export `componentVariants` alongside the component — consumers may need it
- `VariantProps<typeof variants>` auto-generates the correct prop types
- `defaultVariants` ensures the component works with zero props
- Use `compoundVariants` for combination-specific overrides
- `className` in `cn(variants({ ...variantProps }), className)` always comes last

---

## 4. Compound Component Pattern

For complex UI elements with related sub-components (Card, Dialog, Form),
use the compound component pattern.

### Structure

```
src/components/shared/data-card/
├── index.ts           # Barrel export
├── DataCard.tsx        # Main wrapper
├── DataCardHeader.tsx  # Sub-component
├── DataCardBody.tsx    # Sub-component
├── DataCardFooter.tsx  # Sub-component
└── types.ts           # Shared types (if complex)
```

### Implementation

```typescript
// DataCard.tsx
const DataCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded bg-white text-gray-800 shadow-sm border border-slate-200', className)}
      {...props}
    />
  ),
);
DataCard.displayName = 'DataCard';

// DataCardHeader.tsx
const DataCardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col space-y-1.5 p-6', className)}
      {...props}
    />
  ),
);
DataCardHeader.displayName = 'DataCardHeader';

// DataCardTitle.tsx
const DataCardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-lg font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  ),
);
DataCardTitle.displayName = 'DataCardTitle';

// DataCardDescription.tsx
const DataCardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-gray-500', className)}
      {...props}
    />
  ),
);
DataCardDescription.displayName = 'DataCardDescription';

// DataCardContent.tsx
const DataCardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  ),
);
DataCardContent.displayName = 'DataCardContent';

// DataCardFooter.tsx
const DataCardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center p-6 pt-0', className)}
      {...props}
    />
  ),
);
DataCardFooter.displayName = 'DataCardFooter';
```

### Barrel export

```typescript
// index.ts
export { DataCard } from './DataCard';
export { DataCardHeader } from './DataCardHeader';
export { DataCardTitle } from './DataCardTitle';
export { DataCardDescription } from './DataCardDescription';
export { DataCardContent } from './DataCardContent';
export { DataCardFooter } from './DataCardFooter';
```

### Consumer usage

```tsx
import {
  DataCard,
  DataCardHeader,
  DataCardTitle,
  DataCardDescription,
  DataCardContent,
  DataCardFooter,
} from '@/components/shared/data-card';

<DataCard>
  <DataCardHeader>
    <DataCardTitle>Agent Overview</DataCardTitle>
    <DataCardDescription>Summary of active voice agents</DataCardDescription>
  </DataCardHeader>
  <DataCardContent>
    {/* Main content */}
  </DataCardContent>
  <DataCardFooter>
    <Button variant="outline">Cancel</Button>
    <Button>Save</Button>
  </DataCardFooter>
</DataCard>
```

---

## 5. Input Composition Pattern

For input components with addons (icons, clear buttons, loading spinners),
use a container + slot pattern.

### Implementation

```typescript
interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'>,
    VariantProps<typeof inputVariants> {
  allowClear?: boolean;
  loading?: boolean;
  containerClassName?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      className,
      containerClassName,
      allowClear,
      loading,
      leftIcon,
      rightIcon,
      size = 'md',
      disabled,
      value: controlledValue,
      defaultValue,
      onChange,
      ...props
    },
    ref,
  ) => {
    const [value, setValue] = React.useState(controlledValue ?? defaultValue ?? '');

    React.useEffect(() => {
      if (controlledValue !== undefined) setValue(controlledValue);
    }, [controlledValue]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setValue(e.target.value);
      onChange?.(e);
    };

    const handleClear = () => {
      setValue('');
      onChange?.({ target: { value: '' } } as React.ChangeEvent<HTMLInputElement>);
    };

    return (
      <div className={cn('relative flex w-full', containerClassName)}>
        {/* Left icon slot */}
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
            {leftIcon}
          </div>
        )}

        <input
          ref={ref}
          className={cn(
            inputVariants({ size, disabled }),
            leftIcon && 'pl-10',
            (allowClear || rightIcon || loading) && 'pr-10',
            className,
          )}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          {...props}
        />

        {/* Right slot: loading > clear > rightIcon */}
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
          </div>
        )}
        {!loading && allowClear && value && !disabled && (
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-800"
            onClick={handleClear}
            tabIndex={-1}
          >
            <X className="h-4 w-4" />
          </button>
        )}
        {!loading && !allowClear && rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
            {rightIcon}
          </div>
        )}
      </div>
    );
  },
);
SearchInput.displayName = 'SearchInput';
```

**Key rules:**
- Use `containerClassName` for outer div styling, `className` for the input itself
- Controlled + uncontrolled support: accept `value` and `defaultValue`
- Sync controlled value in `useEffect`
- Right slot priority: loading > clear > custom icon (never show more than one)
- Clear button uses `tabIndex={-1}` to avoid disrupting tab order

---

## 6. Radix UI Wrapper Pattern

When wrapping Radix UI primitives for the project's design system:

### Re-export unchanged primitives

```typescript
import { Root, Trigger, Close } from '@radix-ui/react-dialog';

// No styling needed — re-export directly
const Dialog = Root;
const DialogTrigger = Trigger;
const DialogClose = Close;
```

### Style the visual primitives

```typescript
const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof Overlay>,
  React.ComponentPropsWithoutRef<typeof Overlay>
>(({ className, ...props }, ref) => (
  <Overlay
    ref={ref}
    className={cn(
      'fixed inset-0 z-50 bg-black/80',
      'data-[state=open]:animate-in data-[state=closed]:animate-out',
      'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
      className,
    )}
    {...props}
  />
));
DialogOverlay.displayName = 'DialogOverlay';
```

### Data attribute selectors

Radix UI uses `data-state` attributes for open/closed states. Use Tailwind's
data attribute syntax:

```typescript
// Accordion trigger icon rotation
className={cn(
  'transition-transform duration-200',
  '[&[data-state=open]]:rotate-180',
)}

// Content animation
className={cn(
  'overflow-hidden',
  'data-[state=open]:animate-in data-[state=closed]:animate-out',
  'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
)}
```

---

## 7. Loading State Pattern

### Button loading

```typescript
import { Loader2 } from 'lucide-react';

<button disabled={loading || disabled}>
  {loading && <Loader2 className={cn('mr-2 h-4 w-4 animate-spin', loaderClassName)} />}
  {!loading && leftIcon}
  {children}
</button>
```

### Skeleton loading (for content areas)

```typescript
const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('animate-pulse rounded bg-gray-100', className)}
      {...props}
    />
  ),
);
Skeleton.displayName = 'Skeleton';

// Usage
<Skeleton className="h-4 w-[200px]" />
<Skeleton className="h-[42px] w-full" />
```

---

## 8. Slot Pattern (Polymorphic rendering)

Use `@radix-ui/react-slot` when a component needs to render as a different element
(e.g., a Button that renders as an `<a>` for links).

```typescript
import { Slot } from '@radix-ui/react-slot';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        ref={ref}
        className={cn('inline-flex items-center justify-center rounded', className)}
        {...props}
      />
    );
  },
);

// Usage: renders as <a> but inherits all Button styles
<Button asChild>
  <a href="/home">Go Home</a>
</Button>
```

---

## 9. Accessibility Patterns

### Focus management

```typescript
// Focus ring — applied on keyboard focus only (not click)
'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2'

// Skip for decorative elements
'focus:outline-none'  // Only when element is not interactive
```

### ARIA for custom controls

```typescript
// Toggle button
<button
  role="switch"
  aria-checked={isOn}
  onClick={() => setIsOn(!isOn)}
>

// Dialog
<DialogContent aria-describedby="dialog-description">
  <DialogTitle>Confirm Delete</DialogTitle>
  <p id="dialog-description">This action cannot be undone.</p>
</DialogContent>

// Loading state
<button aria-busy={loading} aria-disabled={loading || disabled}>
```

### Screen reader only text

```typescript
const srOnly = 'absolute h-px w-px overflow-hidden whitespace-nowrap border-0 p-0 [clip:rect(0,0,0,0)]';

<span className={srOnly}>Close dialog</span>
```

---

## 10. File Naming & Export Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Single component file | PascalCase | `StatusBadge.tsx` |
| Compound component dir | kebab-case | `data-card/` |
| Barrel export file | `index.ts` | `data-card/index.ts` |
| Type file | `types.ts` | `data-card/types.ts` |
| Component export | Named + default | `export { Badge }; export default Badge;` |
| Variant export | Named only | `export { badgeVariants };` |
| Component location | `src/components/shared/` | `src/components/shared/StatusBadge.tsx` |

### Import paths

```typescript
// cn utility
import { cn } from '@/lib/utils';

// theme constants (presets, semantic aliases, raw colors)
import { presets, semantic, colors } from '@/lib/theme';

// shadcn primitives
import { Button } from '@/components/ui/button';

// shared components
import { StatusBadge } from '@/components/shared/StatusBadge';

// lucide icons
import { Search, X, Loader2, ChevronDown } from 'lucide-react';
```

---

## 11. Using Theme Constants (`src/lib/theme.ts`)

The `theme.ts` file is the **single source of truth** for all design tokens. It exports
three layers: `colors` (raw palette), `semantic` (intent-based aliases), and `presets`
(pre-built class strings). Every component MUST import from `@/lib/theme` instead of
hardcoding class strings.

### Presets — pre-built class strings for common patterns

```typescript
import { cn } from '@/lib/utils';
import { presets } from '@/lib/theme';

// Button with preset base + variant + size
<button className={cn(presets.button.base, presets.button.primary, presets.button.size.md, className)}>
  Save
</button>

// Card using preset
<div className={cn(presets.card.padded, className)}>
  <h3 className={presets.text.heading}>Title</h3>
  <p className={presets.text.secondary}>Description</p>
</div>

// Badge using preset
<span className={cn(presets.badge.base, presets.badge.success)}>Active</span>

// Input using preset
<input className={cn(presets.input.base, presets.input.size.md, className)} />
```

### Semantic aliases — intent-based color references

Use `semantic` for one-off styling where presets don't apply:

```typescript
import { semantic } from '@/lib/theme';

// Dynamic class construction with template literals
<div className={`bg-${semantic.primaryTint} border-${semantic.border}`}>
  <span className={`text-${semantic.textSecondary}`}>Muted label</span>
</div>

// Conditional intent-based styling
<span className={cn(
  `text-${semantic.textPrimary}`,
  isError && `text-${semantic.destructive}`,
  isSuccess && `text-${semantic.success}`,
)}>
  {message}
</span>
```

### Presets with CVA — variant classes from theme

```typescript
import { cva, type VariantProps } from 'class-variance-authority';
import { presets } from '@/lib/theme';

const buttonVariants = cva(presets.button.base, {
  variants: {
    variant: {
      primary: presets.button.primary,
      secondary: presets.button.secondary,
      outline: presets.button.outline,
      ghost: presets.button.ghost,
      destructive: presets.button.destructive,
      link: presets.button.link,
    },
    size: {
      sm: presets.button.size.sm,
      md: presets.button.size.md,
      lg: presets.button.size.lg,
    },
  },
  defaultVariants: {
    variant: 'primary',
    size: 'md',
  },
});
```

### When to use which layer

| Layer | When to use | Example |
|-------|------------|---------|
| `presets` | Standard UI patterns (buttons, inputs, cards, badges, text) | `cn(presets.button.base, presets.button.primary)` |
| `semantic` | Intent-based one-off styling, dynamic classes | `bg-${semantic.primaryTint}` |
| `colors` | Raw palette access (rarely needed) | `colors.purple[500]` → `'purple-500'` |
| Direct Tailwind classes | When no preset/semantic exists | `'flex items-center gap-2'` |

**Rule**: If a preset exists for your use case, use it. Presets ensure consistency and make
global style changes trivial (change the preset, update everywhere).

---

## Pattern Decision Tree

Use this to determine which pattern(s) a new component needs:

```
Does it render a single DOM element?
  └─ Yes → Use forwardRef pattern (#2)

Does it have multiple visual variants (e.g., primary/secondary/outline)?
  └─ Yes → Use CVA pattern (#3)

Does it have multiple related sub-components (header, body, footer)?
  └─ Yes → Use compound component pattern (#4)

Does it have input addons (icons, clear button, loading)?
  └─ Yes → Use input composition pattern (#5)

Does it wrap a Radix UI primitive?
  └─ Yes → Use Radix wrapper pattern (#6)

Does it need to render as different HTML elements?
  └─ Yes → Use slot pattern (#8)

All components:
  → Use cn() for all className composition (#1)
  → Import presets/semantic from @/lib/theme (#11)
  → Include className prop for consumer overrides
  → Set displayName
  → Use theme CSS variables (never hardcoded hex)
  → Include accessibility attributes (#9)
```

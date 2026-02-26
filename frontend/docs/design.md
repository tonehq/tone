# Design System Reference

Latest theme tokens, spacing conventions, and component patterns for the Tone frontend.

---

## Theme Tokens (CSS Variables)

Defined in `src/app/globals.css`. All colors use HSL via `hsl(var(--token))`.

### Light mode (`:root`)

| Token | HSL Value | Usage |
| --- | --- | --- |
| `--background` | `0 0% 100%` | Page backgrounds |
| `--foreground` | `240 10% 3.9%` | Primary text |
| `--card` | `0 0% 100%` | Card surfaces |
| `--card-foreground` | `240 10% 3.9%` | Card text |
| `--popover` | `0 0% 100%` | Dropdown/popover surfaces |
| `--popover-foreground` | `240 10% 3.9%` | Dropdown text |
| `--primary` | `239 84% 67%` | Primary actions, focus rings (violet) |
| `--primary-foreground` | `0 0% 98%` | Text on primary bg |
| `--secondary` | `240 4.8% 95.9%` | Secondary backgrounds |
| `--secondary-foreground` | `240 5.9% 10%` | Text on secondary bg |
| `--muted` | `240 4.8% 95.9%` | Muted backgrounds, disabled states |
| `--muted-foreground` | `240 3.8% 46.1%` | Secondary/helper text |
| `--accent` | `240 4.8% 95.9%` | Hover states, active menu items |
| `--accent-foreground` | `240 5.9% 10%` | Text on accent bg |
| `--destructive` | `0 84.2% 60.2%` | Error states, danger actions |
| `--destructive-foreground` | `0 0% 98%` | Text on destructive bg |
| `--border` | `240 5.9% 90%` | All borders |
| `--input` | `240 5.9% 90%` | Input borders |
| `--ring` | `239 84% 67%` | Focus rings |
| `--sidebar` | `0 0% 98%` | Sidebar background |
| `--sidebar-foreground` | `240 5.3% 26.1%` | Sidebar text |
| `--sidebar-accent` | `240 4.8% 95.9%` | Active sidebar item bg |
| `--radius` | `0.625rem` | Base border radius |

### Tailwind usage

Use semantic color classes that map to CSS vars:

```
text-foreground          # Primary text
text-muted-foreground    # Secondary/description text
bg-background            # Page background
bg-muted                 # Muted sections, banners
bg-accent                # Hover/active states
border-border            # All borders
bg-primary               # Primary buttons, active indicators
text-primary             # Primary color text
bg-destructive           # Danger buttons
```

---

## Semantic Color Accents

Beyond the CSS variable tokens, these Tailwind utility colors are used for domain-specific styling:

| Domain | Color | Tailwind classes |
| --- | --- | --- |
| Inbound agent | Emerald | `border-emerald-200 bg-emerald-50 text-emerald-700` |
| Outbound agent | Violet | `border-violet-200 bg-violet-50 text-violet-700` |
| Success states | Emerald | `bg-emerald-50 text-emerald-600` |
| Active calls | Emerald | `text-emerald-500 bg-emerald-500/10` |
| Analytics | Blue | `text-blue-500 bg-blue-500/10` |
| Warnings | Amber | `text-amber-500 bg-amber-500/10` |

---

## Typography Scale

| Element | Classes | Size |
| --- | --- | --- |
| Page title | `text-2xl font-bold tracking-tight text-foreground` | 24px |
| Section heading | `text-lg font-semibold text-foreground` | 18px |
| Card/form heading | `text-sm font-semibold text-foreground` | 14px |
| Body text | `text-sm text-foreground` | 14px |
| Description/helper text | `text-[13px] leading-relaxed text-muted-foreground` | 13px |
| Small labels | `text-xs text-muted-foreground` | 12px |
| Stat values | `text-3xl font-bold tracking-tight text-foreground` | 30px |

---

## Spacing Standards

### Form layouts

| Element | Class | Value |
| --- | --- | --- |
| Between form rows | `mb-6` | 1.5rem |
| Section container | `py-4` | 1rem vertical |
| Tab content area | `px-8 py-6` | 2rem / 1.5rem |
| Description below label | `mt-0.5` | 0.125rem |
| Form row gap (label/control) | `gap-6` | 1.5rem |
| Form row split | `flex-[0_0_55%]` / `flex-[0_0_40%]` | 55/40 |

### Page layouts

| Element | Class | Value |
| --- | --- | --- |
| Page padding | `p-6 lg:p-8` | 1.5rem / 2rem |
| Section spacing | `space-y-8` | 2rem |
| Card grid gap | `gap-4` | 1rem |
| Alert/banner padding | `px-6 py-2.5` | Compact |
| Header bar padding | `px-6 py-4` | Standard |

### Sidebar

| Element | Class | Value |
| --- | --- | --- |
| Sidebar width | `w-[280px]` | 280px |
| Back button area | `px-3 py-2` | Compact |
| Agent info section | `px-4 py-4` | Standard |
| Nav item spacing | `space-y-0.5` | 0.125rem |
| Nav item padding | `px-3 py-2` | Standard |

---

## Border Radius

Controlled by the `--radius` CSS variable (`0.625rem` = 10px):

| Token | Class | Computed |
| --- | --- | --- |
| `--radius-sm` | `rounded-sm` | 6px |
| `--radius-md` | `rounded-md` | 8px |
| `--radius-lg` | `rounded-lg` | 10px |
| `--radius-xl` | `rounded-xl` | 14px |

---

## Component Patterns

### Buttons

Always use `CustomButton` from `@/components/shared`:

```tsx
<CustomButton type="primary">Save</CustomButton>         // Violet filled
<CustomButton type="default">Cancel</CustomButton>        // Outlined
<CustomButton type="text">Back</CustomButton>              // Ghost/text
<CustomButton type="danger">Delete</CustomButton>          // Red filled
<CustomButton type="primary" loading>Saving...</CustomButton>  // With spinner
<CustomButton type="primary" icon={<Save size={16} />}>Save</CustomButton>  // With icon
```

### Agent type badge

Always use `AgentTypeBadge` from `@/components/agents/AgentTypeBadge`:

```tsx
<AgentTypeBadge agentType="inbound" />   // Emerald + PhoneIncoming icon
<AgentTypeBadge agentType="outbound" />  // Violet + PhoneOutgoing icon
```

### Form row

Standard 55/40 split layout for settings-style forms:

```tsx
<div className="mb-6 flex items-start justify-between gap-6">
  <div className="flex-[0_0_55%]">
    <h3 className="text-sm font-semibold text-foreground">Label</h3>
    <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">Description</p>
  </div>
  <div className="flex-[0_0_40%]">{/* Control */}</div>
</div>
```

### Loading states

Use `Loader2` from lucide-react with `animate-spin`:

```tsx
<Loader2 className="size-6 animate-spin text-muted-foreground" />
```

### Active/selected states

Use `cn()` with conditional classes:

```tsx
className={cn(
  'rounded-md border p-2 transition-colors',
  isActive
    ? 'border-primary bg-primary/10'
    : 'border-border hover:border-muted-foreground/50',
)}
```

### Card radio groups

For mutually exclusive card-style selections:

```tsx
<div className="flex gap-2" role="radiogroup" aria-label="Selection">
  {options.map((item) => (
    <button
      key={item.value}
      type="button"
      role="radio"
      aria-checked={selected === item.value}
      className={cn(
        'rounded-md border p-2 text-left transition-colors',
        selected === item.value
          ? 'border-primary bg-primary/10'
          : 'border-border hover:border-muted-foreground/50',
      )}
      onClick={() => onSelect(item.value)}
    >
      <span className="block text-sm font-semibold text-foreground">{item.label}</span>
      <span className="block text-xs text-muted-foreground">{item.desc}</span>
    </button>
  ))}
</div>
```

---

## Icon Usage

Use **lucide-react** for all icons. Common sizes:

| Context | Size prop |
| --- | --- |
| Inline with text (buttons) | `size={16}` |
| Toolbar icons | `size={18}` |
| Stat card icons | `size={18}` |
| Small indicators | `size={12}` |
| Large loading spinner | `size={40}` or `className="size-10"` |

---

## Animations

Defined in `globals.css`:

| Class | Effect |
| --- | --- |
| `animate-page` | `slideUp` 0.3s — page entrance |
| `animate-fadeIn` | `fadeIn` 0.3s — element appearance |
| `animate-spin` | Tailwind built-in — loading spinners |
| `transition-colors` | Smooth color transitions on hover/active |
| `transition-all` | All properties transition |

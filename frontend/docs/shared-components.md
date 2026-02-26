# Shared Components Reference

Single source of truth for `@/components/shared` components. Use this file to understand APIs and usage without reading each component file (reduces token usage).

**Import from:** `@/components/shared` (barrel) or `@/components/shared/<ComponentName>`.

---

## TextInput

Wraps shadcn `Input` + `Label`. Supports password visibility toggle.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| name | string | — | **Required.** Input name and id. |
| type | string | `'text'` | Input type. `'password'` shows show/hide toggle. |
| label | string | — | Label text above input. |
| isRequired | boolean | `false` | Shows asterisk, sets aria. |
| loading | boolean | `false` | Shows skeleton instead of input. |
| error | boolean | `false` | Destructive border + ring. |
| helperText | string | — | Small text below input. |
| labelClassName | string | — | Class for the label. |
| className | string | — | Class for the input. |
| + all native input props | | | placeholder, value, defaultValue, onChange, disabled, etc. |

**Example:**
```tsx
<TextInput name="email" type="email" label="Email" placeholder="Enter email" isRequired />
<TextInput name="password" type="password" label="Password" isRequired error={!!err} helperText={err} />
```

---

## CustomButton

Wraps shadcn `Button` with semantic `type` and loading/icon support.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| children | ReactNode | — | Button label. |
| type | `'primary' \| 'default' \| 'text' \| 'link' \| 'danger'` | `'default'` | Maps to shadcn variant (default→outline, primary→default, etc.). |
| htmlType | `'button' \| 'submit' \| 'reset'` | `'button'` | Native button type. |
| loading | boolean | `false` | Shows Loader2 spinner, disables button. |
| icon | ReactNode | — | Rendered before children (hidden when loading). |
| fullWidth | boolean | `false` | `w-full`. |
| className | string | — | Merged with variant classes. |
| + button props | | | onClick, disabled, etc. |

**Example:**
```tsx
<CustomButton type="primary" htmlType="submit" fullWidth>Continue</CustomButton>
<CustomButton type="default" icon={<GoogleIcon className="size-4" />}>Continue with Google</CustomButton>
```

---

## CustomLink

`next/link` styled like CustomButton `type="link"` (primary text, underline on hover). No navigation logic—just styling.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| href | string | — | **Required.** Next.js Link href. |
| children | ReactNode | — | Link text. |
| icon | ReactNode | — | Rendered before children. |
| fullWidth | boolean | `false` | `w-full`. |
| className | string | — | Override classes. |
| + Next.js Link props | | | prefetch, replace, etc. |

**Example:**
```tsx
<CustomLink href="/auth/forgotpassword">Forgot password?</CustomLink>
<CustomLink href="/signup" icon={<Icon />}>Sign up</CustomLink>
```

---

## Form

Simple form wrapper that collects native input values and calls `onFinish(values)` on submit. No validation—just `FormData` → object.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| children | ReactNode | — | Form content (inputs must have `name`). |
| onFinish | (values: Record<string, any>) => void | — | **Required.** Called with key-value map from form. |
| layout | `'horizontal' \| 'vertical'` | `'vertical'` | Flex direction. |
| autoComplete | string | `'off'` | Form autocomplete. |
| className | string | — | Applied to `<form>`. |

**Example:**
```tsx
<Form onFinish={(values) => login(values.email, values.password)} layout="vertical">
  <TextInput name="email" label="Email" />
  <TextInput name="password" type="password" label="Password" />
  <CustomButton type="primary" htmlType="submit">Submit</CustomButton>
</Form>
```

---

## CheckboxField

Checkbox + label + optional helper/error. Uses shadcn `Checkbox` and `Label`.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| id | string | — | **Required.** Checkbox id (and Label htmlFor). |
| label | string | — | Label text next to checkbox. |
| isRequired | boolean | `false` | Asterisk + aria. |
| loading | boolean | `false` | Skeleton for checkbox + label. |
| error | boolean | `false` | Destructive border/ring on checkbox. |
| helperText | string | — | Small text below. |
| labelClassName | string | — | Class for label. |
| className | string | — | Class for checkbox. |
| + Checkbox props | | | checked, defaultChecked, onCheckedChange, disabled, etc. |

**Example:**
```tsx
<CheckboxField id="remember" label="Remember me" defaultChecked />
<CheckboxField id="terms" label="I agree" isRequired error={!!err} helperText={err} />
```

---

## RadioGroupField

Single-choice group. Uses shadcn `RadioGroup` + `RadioGroupItem` + `Label` per option.

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| name | string | — | **Required.** Group name. |
| options | RadioGroupOption[] | — | **Required.** `{ value, label, disabled? }[]`. |
| label | string | — | Label above the group. |
| value | string | — | Controlled value. |
| defaultValue | string | — | Uncontrolled default. |
| onValueChange | (value: string) => void | — | Controlled callback. |
| isRequired | boolean | `false` | Asterisk + aria. |
| loading | boolean | `false` | Skeleton for label + options. |
| error | boolean | `false` | Invalid state on items. |
| helperText | string | — | Small text below group. |
| labelClassName | string | — | Class for group label. |
| orientation | `'horizontal' \| 'vertical'` | `'vertical'` | Layout of options. |
| disabled | boolean | `false` | Disable whole group. |
| className | string | — | Class for RadioGroup root. |

**RadioGroupOption:** `{ value: string; label: string; disabled?: boolean }`

**Example:**
```tsx
<RadioGroupField
  name="plan"
  label="Plan"
  options={[{ value: 'm', label: 'Monthly' }, { value: 'y', label: 'Yearly' }]}
  defaultValue="m"
  onValueChange={setPlan}
  orientation="vertical"
/>
```

---

## Exports from `@/components/shared`

- **Components:** `CheckboxField`, `CustomButton`, `CustomLink`, `Form`, `RadioGroupField`, `TextInput`
- **Types:** `RadioGroupOption` (from RadioGroupField)

---

*When adding or changing shared components, update this file so that docs stay the single source of truth and token usage stays low.*

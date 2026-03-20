# Shared Components Reference

Single source of truth for `@/components/shared` components. Use this file to understand APIs and usage without reading each component file (reduces token usage).

**Import from:** `@/components/shared` (barrel) or `@/components/shared/<ComponentName>`.

**Types location:** All component prop interfaces live in `@/types/components`. They are re-exported from `@/components/shared` for convenience.

---

## CustomTable

Reusable data table built on shadcn `Table` primitives. API follows Ant Design Table conventions (`columns`, `dataSource`, `rowKey`, `render`, `pagination`). Includes built-in client-side search, sorting, pagination, loading skeleton, and empty state. The table takes only its content height (no `flex-1` stretch) — when rows are few, no empty space appears below; scrolling activates only when content exceeds the viewport.

### Props

| Prop              | Type                                           | Default               | Description                                                                |
| ----------------- | ---------------------------------------------- | --------------------- | -------------------------------------------------------------------------- |
| columns           | `CustomTableColumn<TRow>[]`                    | —                     | **Required.** Column definitions (see below).                              |
| dataSource        | `TRow[]`                                       | —                     | **Required.** Array of row data objects.                                   |
| rowKey            | `string \| (record: TRow) => string \| number` | —                     | **Required.** Property name or function that returns a unique key per row. |
| loading           | boolean                                        | `false`               | Shows animated skeleton rows.                                              |
| skeletonRows      | number                                         | `5`                   | Number of skeleton rows to display while loading.                          |
| searchable        | boolean                                        | `false`               | Shows a search input above the table.                                      |
| searchPlaceholder | string                                         | `'Search...'`         | Placeholder text for search input.                                         |
| pagination        | `CustomTablePagination \| false`               | uncontrolled defaults | Pagination config object (see below). Set `false` to disable.              |
| emptyState        | ReactNode                                      | `'No results found.'` | Content shown when `dataSource` is empty and not loading.                  |
| onRow             | `(record, index) => { onClick? }`              | —                     | Returns event handlers for each row (e.g. click navigation).               |
| className         | string                                         | —                     | Class for the outer wrapper.                                               |

### CustomTableColumn

| Field     | Type                                      | Default  | Description                                                       |
| --------- | ----------------------------------------- | -------- | ----------------------------------------------------------------- |
| key       | string                                    | —        | **Required.** Unique column identifier (React key).               |
| title     | string                                    | —        | **Required.** Column header text.                                 |
| dataIndex | `keyof TRow`                              | —        | Property name to read the cell value from.                        |
| render    | `(value, record, index) => ReactNode`     | —        | Custom cell renderer. Receives `(rawValue, rowObject, rowIndex)`. |
| align     | `'left' \| 'center' \| 'right'`           | `'left'` | Text alignment for header and cells.                              |
| sorter    | `boolean \| (a: TRow, b: TRow) => number` | —        | `true` for default sort; a function for custom compare.           |
| className | string                                    | —        | Extra class for header and cells.                                 |
| width     | string                                    | —        | Tailwind width class (e.g. `'w-48'`).                             |
| hidden    | boolean                                   | `false`  | Hides the column.                                                 |

### CustomTablePagination

| Field           | Type                       | Default        | Description                                              |
| --------------- | -------------------------- | -------------- | -------------------------------------------------------- |
| current         | number                     | `1`            | Current page (1-indexed).                                |
| pageSize        | number                     | `10`           | Rows per page.                                           |
| total           | number                     | —              | Total items (enables server-driven pagination when set). |
| pageSizeOptions | `number[]`                 | `[10, 20, 50]` | Options for the page size dropdown.                      |
| onChange        | `(page, pageSize) => void` | —              | Called when page or pageSize changes (controlled mode).  |

**Pagination behavior:**

- **Uncontrolled (default):** Omit the `pagination` prop entirely. The table manages page/pageSize internally with defaults (page 1, pageSize 10).
- **Controlled:** Pass a `pagination` object with `current`, `pageSize`, and `onChange`. The table calls `onChange` on every page/size change.
- **Server-driven:** Set `pagination.total` to the backend total count. The table displays the correct "X of Y" text. Your `onChange` handler should fetch the appropriate page from the API.
- **Disabled:** Set `pagination={false}` to show all rows without pagination controls.

### Example

```tsx
import { CustomTable, CustomTableColumn } from '@/components/shared';

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
}

const columns: CustomTableColumn<User>[] = [
  { key: 'name', title: 'Name', dataIndex: 'name', sorter: true },
  { key: 'email', title: 'Email', dataIndex: 'email' },
  {
    key: 'role',
    title: 'Role',
    dataIndex: 'role',
    render: (value) => <Badge>{value as string}</Badge>,
  },
  {
    key: 'actions',
    title: '',
    align: 'right',
    render: (_value, record) => <ActionMenu user={record} />,
  },
];

<CustomTable
  columns={columns}
  dataSource={users}
  rowKey="id"
  loading={isLoading}
  searchable
  searchPlaceholder="Search users..."
  pagination={{ current: page, pageSize: 10, total: totalCount, onChange: setPage }}
  emptyState={<p>No users found.</p>}
  onRow={(record) => ({ onClick: () => router.push(`/users/${record.id}`) })}
/>;
```

### Do's and Don'ts

- **Do** use `CustomTable` for all tabular data across the app.
- **Do** define columns with explicit `key` values (not array index).
- **Do** use `render` for any cell that needs custom formatting (dates, badges, action menus).
- **Don't** use MUI DataGrid, Ant Design Table, or raw `<table>` elements — always use `CustomTable`.
- **Don't** put search logic outside the table if `searchable` covers your use case.
- **Don't** set both `dataIndex` and `render` if `render` ignores the value — omit `dataIndex` for action columns.

---

## CustomModal

Reusable modal dialog built on shadcn `Dialog`. Supports title, description, custom content, confirm/cancel actions, loading state, and custom footer.

### Props

| Prop            | Type                    | Default         | Description                                                                  |
| --------------- | ----------------------- | --------------- | ---------------------------------------------------------------------------- |
| open            | boolean                 | —               | **Required.** Whether the modal is visible.                                  |
| onClose         | `() => void`            | —               | **Required.** Called when the modal should close.                            |
| title           | ReactNode               | —               | Title in the dialog header.                                                  |
| description     | string                  | —               | Description text below the title.                                            |
| children        | ReactNode               | —               | Modal body content.                                                          |
| footer          | `ReactNode \| null`     | —               | Custom footer. `null` hides footer. Omit for default confirm/cancel buttons. |
| confirmText     | string                  | `'Confirm'`     | Label for the confirm button.                                                |
| cancelText      | string                  | `'Cancel'`      | Label for the cancel button.                                                 |
| onConfirm       | `() => void`            | —               | Called when confirm is clicked.                                              |
| onCancel        | `() => void`            | `onClose`       | Called when cancel is clicked. Falls back to `onClose`.                      |
| confirmLoading  | boolean                 | `false`         | Shows spinner on confirm button and disables it.                             |
| confirmType     | `'primary' \| 'danger'` | `'primary'`     | Confirm button variant.                                                      |
| confirmDisabled | boolean                 | `false`         | Disables the confirm button.                                                 |
| hideFooter      | boolean                 | `false`         | Hides the footer entirely (same as `footer={null}`).                         |
| width           | string                  | `'sm:max-w-lg'` | Max-width Tailwind class for the dialog.                                     |
| className       | string                  | —               | Extra class for `DialogContent`.                                             |
| showCloseButton | boolean                 | `true`          | Show the built-in X close button.                                            |

### Behavior

- **Default footer:** When `footer` is omitted, shows Cancel + Confirm buttons using `CustomButton`.
- **Custom footer:** Pass any ReactNode as `footer` to fully replace the default buttons.
- **No footer:** Set `hideFooter` or `footer={null}` for content-only modals (e.g. selection modals).
- **Controlled:** The modal is always controlled via `open` / `onClose`. Clicking the overlay or X button triggers `onClose`.
- **Loading:** When `confirmLoading` is true, the confirm button shows a spinner and both buttons are disabled to prevent double submission.

### Examples

```tsx
import { CustomModal, CustomButton } from '@/components/shared';

{
  /* Confirmation dialog with default footer */
}
<CustomModal
  open={deleteOpen}
  onClose={() => setDeleteOpen(false)}
  title="Delete Item"
  description="Are you sure? This action cannot be undone."
  confirmText="Delete"
  confirmType="danger"
  confirmLoading={deleting}
  onConfirm={handleDelete}
/>;

{
  /* Content-only modal (no footer) */
}
<CustomModal
  open={selectorOpen}
  onClose={() => setSelectorOpen(false)}
  title="Choose an option"
  hideFooter
>
  <div className="grid grid-cols-2 gap-3">
    <OptionCard onClick={() => handleSelect('a')} />
    <OptionCard onClick={() => handleSelect('b')} />
  </div>
</CustomModal>;

{
  /* Form modal with custom footer */
}
<CustomModal
  open={formOpen}
  onClose={() => setFormOpen(false)}
  title="Edit Profile"
  footer={
    <>
      <CustomButton type="default" onClick={() => setFormOpen(false)}>
        Cancel
      </CustomButton>
      <CustomButton type="primary" loading={saving} onClick={handleSave}>
        Save
      </CustomButton>
    </>
  }
>
  <TextInput name="name" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
</CustomModal>;
```

### Do's and Don'ts

- **Do** use `CustomModal` for all dialogs, confirmations, and overlays across the app.
- **Do** use `confirmType="danger"` for destructive actions (delete, remove, revoke).
- **Do** provide `description` for confirmation dialogs to explain the consequence.
- **Don't** use shadcn `Dialog` directly — always use `CustomModal`.
- **Don't** build inline Snackbar/Alert state for delete confirmations — use `CustomModal` instead.
- **Don't** set `onConfirm` without also handling `confirmLoading` for async operations.

---

## TextInput

Wraps shadcn `Input` + `Label`. Supports password visibility toggle, loading skeleton, error state, and helper text. **Unified component** — when a `control` prop (from `react-hook-form`) is provided, it automatically wraps the input in an RHF `Controller`, eliminating the need for a separate form wrapper component.

### Plain mode (no `control`)

Standard controlled/uncontrolled input. Renders as a single `<div>` container (label + input + helperText), so `space-y-*` on a parent form adds gaps between fields.

| Prop                     | Type      | Default  | Description                                                    |
| ------------------------ | --------- | -------- | -------------------------------------------------------------- |
| name                     | string    | —        | **Required.** Input name and id.                               |
| type                     | string    | `'text'` | Input type. `'password'` shows show/hide toggle.               |
| label                    | string    | —        | Label text above input.                                        |
| isRequired               | boolean   | `false`  | Shows red asterisk `*` next to label.                          |
| loading                  | boolean   | `false`  | Shows skeleton instead of input.                               |
| error                    | boolean   | `false`  | Destructive border + ring.                                     |
| helperText               | string    | —        | Small text below input (red when `error=true`).                |
| labelClassName           | string    | —        | Class for the label.                                           |
| className                | string    | —        | Class for the input.                                           |
| leftIcon                 | ReactNode | —        | Optional icon on the left (e.g. Search). Adds `pl-9` to input. |
| + all native input props |           |          | placeholder, value, defaultValue, onChange, disabled, etc.     |

### RHF mode (with `control`)

When `control` is provided, the component wraps itself in an RHF `Controller`. Error state and helperText are auto-derived from `fieldState` but can be overridden via props.

| Prop                                                              | Type                      | Default | Description                                         |
| ----------------------------------------------------------------- | ------------------------- | ------- | --------------------------------------------------- |
| name                                                              | string                    | —       | **Required.** RHF field name.                       |
| control                                                           | `Control<any>`            | —       | **Required.** RHF `control` from `useForm`.         |
| rules                                                             | `RegisterOptions`         | —       | RHF validation rules (e.g. `{ required: 'Req.' }`). |
| onValueChange                                                     | `(value: string) => void` | —       | Side-effect callback on value change.               |
| + all plain TextInput props (minus `value`, `onChange`, `onBlur`) |                           |         | Forwarded to the underlying input.                  |

**Important:** When using inside a layout that also renders errors (e.g. `FormRow` with `error` prop), do NOT pass the error to both — let `TextInput` handle error display to avoid duplicate messages.

### Examples

```tsx
{/* Plain usage */}
<TextInput name="email" type="email" label="Email" placeholder="Enter email" isRequired />
<TextInput name="password" type="password" label="Password" isRequired error={!!err} helperText={err} />
<TextInput name="table-search" placeholder="Search..." leftIcon={<Search />} value={q} onChange={(e) => setQ(e.target.value)} />

{/* RHF with rules (agent form) */}
<TextInput
  name="name"
  control={control}
  rules={{ required: 'Name is required' }}
  onValueChange={(v) => onFormChange({ name: v })}
/>

{/* RHF with Zod resolver (auth forms) */}
<TextInput name="email" control={control} label="Email" isRequired />
```

---

## CustomButton

Wraps shadcn `Button` with semantic `type` and loading/icon support.

| Prop           | Type                                                     | Default     | Description                                                      |
| -------------- | -------------------------------------------------------- | ----------- | ---------------------------------------------------------------- |
| children       | ReactNode                                                | —           | Button label.                                                    |
| type           | `'primary' \| 'default' \| 'text' \| 'link' \| 'danger'` | `'default'` | Maps to shadcn variant (default→outline, primary→default, etc.). |
| htmlType       | `'button' \| 'submit' \| 'reset'`                        | `'button'`  | Native button type.                                              |
| loading        | boolean                                                  | `false`     | Shows Loader2 spinner, disables button.                          |
| icon           | ReactNode                                                | —           | Rendered before children (hidden when loading).                  |
| fullWidth      | boolean                                                  | `false`     | `w-full`.                                                        |
| className      | string                                                   | —           | Merged with variant classes.                                     |
| + button props |                                                          |             | onClick, disabled, etc.                                          |

**Example:**

```tsx
<CustomButton type="primary" htmlType="submit" fullWidth>Continue</CustomButton>
<CustomButton type="default" icon={<GoogleIcon className="size-4" />}>Continue with Google</CustomButton>
```

---

## CustomLink

`next/link` styled like CustomButton `type="link"` (primary text, underline on hover). No navigation logic—just styling.

| Prop                 | Type      | Default | Description                      |
| -------------------- | --------- | ------- | -------------------------------- |
| href                 | string    | —       | **Required.** Next.js Link href. |
| children             | ReactNode | —       | Link text.                       |
| icon                 | ReactNode | —       | Rendered before children.        |
| fullWidth            | boolean   | `false` | `w-full`.                        |
| className            | string    | —       | Override classes.                |
| + Next.js Link props |           |         | prefetch, replace, etc.          |

**Example:**

```tsx
<CustomLink href="/auth/forgotpassword">Forgot password?</CustomLink>
<CustomLink href="/signup" icon={<Icon />}>Sign up</CustomLink>
```

---

## Form

Simple form wrapper that collects native input values and calls `onFinish(values)` on submit. No validation—just `FormData` → object. Applies `space-y-5` for vertical spacing between children.

> **Note:** Auth forms (login, signup, forgot password, reset password) use `useForm` + `zodResolver` + `TextInput` (with `control` prop) for proper client-side validation and type safety. See `src/schemas/auth.ts` for Zod schemas. The `Form` component is still used in the agent form (`GeneralTab`).

| Prop         | Type                                  | Default      | Description                                        |
| ------------ | ------------------------------------- | ------------ | -------------------------------------------------- |
| children     | ReactNode                             | —            | Form content (inputs must have `name`).            |
| onFinish     | (values: Record<string, any>) => void | —            | **Required.** Called with key-value map from form. |
| layout       | `'horizontal' \| 'vertical'`          | `'vertical'` | Flex direction.                                    |
| autoComplete | string                                | `'off'`      | Form autocomplete.                                 |
| className    | string                                | —            | Applied to `<form>`.                               |

**Example (legacy — agent form):**

```tsx
<Form onFinish={handleFinish} layout="vertical">
  <TextInput name="email" label="Email" />
  <CustomButton type="primary" htmlType="submit">
    Submit
  </CustomButton>
</Form>
```

**Example (auth forms — RHF + Zod):**

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, type LoginFormData } from '@/schemas/auth';

const { control, handleSubmit } = useForm<LoginFormData>({
  resolver: zodResolver(loginSchema),
  defaultValues: { email: '', password: '' },
});

<form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
  <TextInput name="email" control={control} label="Email" isRequired />
  <TextInput name="password" control={control} type="password" label="Password" isRequired />
  <CustomButton type="primary" htmlType="submit">
    Continue
  </CustomButton>
</form>;
```

---

## CheckboxField

Checkbox + label + optional helper/error. Uses shadcn `Checkbox` and `Label`. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop             | Type    | Default | Description                                              |
| ---------------- | ------- | ------- | -------------------------------------------------------- |
| id               | string  | —       | **Required.** Checkbox id (and Label htmlFor).           |
| label            | string  | —       | Label text next to checkbox.                             |
| isRequired       | boolean | `false` | Asterisk + aria.                                         |
| loading          | boolean | `false` | Skeleton for checkbox + label.                           |
| error            | boolean | `false` | Destructive border/ring on checkbox.                     |
| helperText       | string  | —       | Small text below.                                        |
| labelClassName   | string  | —       | Class for label.                                         |
| className        | string  | —       | Class for checkbox.                                      |
| + Checkbox props |         |         | checked, defaultChecked, onCheckedChange, disabled, etc. |

### RHF mode (with `control`)

Uses the `id` prop as the RHF field name. Error state and helperText are auto-derived from `fieldState`.

| Prop                                                             | Type                         | Default | Description                                   |
| ---------------------------------------------------------------- | ---------------------------- | ------- | --------------------------------------------- |
| id                                                               | string                       | —       | **Required.** Checkbox id and RHF field name. |
| control                                                          | `Control<any>`               | —       | **Required.** RHF `control`.                  |
| rules                                                            | `RegisterOptions`            | —       | RHF validation rules.                         |
| onCheckedChange                                                  | `(checked: boolean) => void` | —       | Side-effect callback.                         |
| + plain CheckboxField props (minus `checked`, `onCheckedChange`) |                              |         | Forwarded.                                    |

### Examples

```tsx
{/* Plain */}
<CheckboxField id="remember" label="Remember me" defaultChecked />
<CheckboxField id="terms" label="I agree" isRequired error={!!err} helperText={err} />

{/* RHF */}
<CheckboxField
  id="terms"
  control={control}
  rules={{ required: 'You must accept' }}
  label="I accept the terms"
/>
```

---

## RadioGroupField

Single-choice group. Uses shadcn `RadioGroup` + `RadioGroupItem` + `Label` per option. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop           | Type                         | Default      | Description                                    |
| -------------- | ---------------------------- | ------------ | ---------------------------------------------- |
| name           | string                       | —            | **Required.** Group name.                      |
| options        | RadioGroupOption[]           | —            | **Required.** `{ value, label, disabled? }[]`. |
| label          | string                       | —            | Label above the group.                         |
| value          | string                       | —            | Controlled value.                              |
| defaultValue   | string                       | —            | Uncontrolled default.                          |
| onValueChange  | (value: string) => void      | —            | Controlled callback.                           |
| isRequired     | boolean                      | `false`      | Asterisk + aria.                               |
| loading        | boolean                      | `false`      | Skeleton for label + options.                  |
| error          | boolean                      | `false`      | Invalid state on items.                        |
| helperText     | string                       | —            | Small text below group.                        |
| labelClassName | string                       | —            | Class for group label.                         |
| orientation    | `'horizontal' \| 'vertical'` | `'vertical'` | Layout of options.                             |
| disabled       | boolean                      | `false`      | Disable whole group.                           |
| className      | string                       | —            | Class for RadioGroup root.                     |

### RHF mode (with `control`)

Error state and helperText are auto-derived from `fieldState`.

| Prop                                                           | Type                         | Default | Description                                                        |
| -------------------------------------------------------------- | ---------------------------- | ------- | ------------------------------------------------------------------ |
| name                                                           | string                       | —       | **Required.** RHF field name.                                      |
| control                                                        | `Control<any>`               | —       | **Required.** RHF `control`.                                       |
| rules                                                          | `RegisterOptions`            | —       | RHF validation rules.                                              |
| onValueChange                                                  | `(value: string) => void`    | —       | Side-effect callback.                                              |
| transformValue                                                 | `(value: string) => unknown` | —       | Converts the string value before passing to RHF (e.g. to boolean). |
| + plain RadioGroupField props (minus `value`, `onValueChange`) |                              |         | Forwarded.                                                         |

**RadioGroupOption:** `{ value: string; label: string; disabled?: boolean }`

### Examples

```tsx
{
  /* Plain */
}
<RadioGroupField
  name="plan"
  label="Plan"
  options={[
    { value: 'm', label: 'Monthly' },
    { value: 'y', label: 'Yearly' },
  ]}
  defaultValue="m"
  onValueChange={setPlan}
  orientation="vertical"
/>;

{
  /* RHF */
}
<RadioGroupField
  name="plan"
  control={control}
  options={[
    { value: 'monthly', label: 'Monthly' },
    { value: 'yearly', label: 'Yearly' },
  ]}
  orientation="horizontal"
/>;

{
  /* RHF with boolean conversion (Yes/No toggle) */
}
<RadioGroupField
  name="enabled"
  control={control}
  options={[
    { value: 'true', label: 'Yes' },
    { value: 'false', label: 'No' },
  ]}
  orientation="horizontal"
  transformValue={(v) => v === 'true'}
/>;
```

---

## SelectInput

Wraps shadcn `Select` + `Label`. Provides loading skeleton, error state, and helper text. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop             | Type                      | Default              | Description                                    |
| ---------------- | ------------------------- | -------------------- | ---------------------------------------------- |
| name             | string                    | —                    | **Required.** Select name and id.              |
| options          | `SelectOption[]`          | —                    | **Required.** `{ value, label, disabled? }[]`. |
| value            | string                    | —                    | Controlled value.                              |
| defaultValue     | string                    | —                    | Uncontrolled default.                          |
| onValueChange    | `(value: string) => void` | —                    | Called when selection changes.                 |
| placeholder      | string                    | `'Select an option'` | Placeholder text when no value selected.       |
| label            | string                    | —                    | Label text above select.                       |
| isRequired       | boolean                   | `false`              | Shows asterisk on label.                       |
| loading          | boolean                   | `false`              | Shows skeleton instead of select.              |
| disabled         | boolean                   | `false`              | Disables the select.                           |
| error            | boolean                   | `false`              | Destructive border + ring.                     |
| helperText       | string                    | —                    | Small text below select.                       |
| size             | `'sm' \| 'default'`       | `'default'`          | Size variant passed to SelectTrigger.          |
| labelClassName   | string                    | —                    | Class for the label.                           |
| className        | string                    | —                    | Class for the outer wrapper div.               |
| triggerClassName | string                    | —                    | Class for the SelectTrigger.                   |

### RHF mode (with `control`)

Error state and helperText are auto-derived from `fieldState`.

| Prop                                                       | Type                      | Default | Description                   |
| ---------------------------------------------------------- | ------------------------- | ------- | ----------------------------- |
| name                                                       | string                    | —       | **Required.** RHF field name. |
| control                                                    | `Control<any>`            | —       | **Required.** RHF `control`.  |
| rules                                                      | `RegisterOptions`         | —       | RHF validation rules.         |
| onValueChange                                              | `(value: string) => void` | —       | Side-effect callback.         |
| + plain SelectInput props (minus `value`, `onValueChange`) |                           |         | Forwarded.                    |

**SelectOption:** `{ value: string; label: string; disabled?: boolean }`

### Examples

```tsx
{
  /* Plain */
}
<SelectInput
  name="provider"
  label="AI Model"
  value={selectedProvider}
  onValueChange={setSelectedProvider}
  placeholder="Select a provider"
  options={providers.map((p) => ({ value: String(p.id), label: p.display_name }))}
  loading={isLoading}
/>;

{
  /* RHF */
}
<SelectInput
  name="provider"
  control={control}
  rules={{ required: 'Select a provider' }}
  options={providerOptions}
  placeholder="Select a provider"
  onValueChange={(v) => handleChange('provider', v)}
/>;
```

---

## TextAreaField

Wraps shadcn `Textarea` + `Label`. Supports loading skeleton, error state, and helper text. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop                        | Type    | Default | Description                         |
| --------------------------- | ------- | ------- | ----------------------------------- |
| name                        | string  | —       | **Required.** Textarea name and id. |
| label                       | string  | —       | Label text above textarea.          |
| isRequired                  | boolean | `false` | Shows asterisk on label.            |
| loading                     | boolean | `false` | Shows skeleton instead of textarea. |
| error                       | boolean | `false` | Destructive border + ring.          |
| helperText                  | string  | —       | Small text below textarea.          |
| rows                        | number  | `3`     | Number of visible text rows.        |
| labelClassName              | string  | —       | Class for the label.                |
| className                   | string  | —       | Class for the textarea.             |
| + all native textarea props |         |         | placeholder, value, onChange, etc.  |

### RHF mode (with `control`)

Error state and helperText are auto-derived from `fieldState`.

| Prop                                                              | Type                      | Default | Description                   |
| ----------------------------------------------------------------- | ------------------------- | ------- | ----------------------------- |
| name                                                              | string                    | —       | **Required.** RHF field name. |
| control                                                           | `Control<any>`            | —       | **Required.** RHF `control`.  |
| rules                                                             | `RegisterOptions`         | —       | RHF validation rules.         |
| onValueChange                                                     | `(value: string) => void` | —       | Side-effect callback.         |
| + plain TextAreaField props (minus `value`, `onChange`, `onBlur`) |                           |         | Forwarded.                    |

### Examples

```tsx
{
  /* Plain */
}
<TextAreaField
  name="description"
  label="Description"
  value={description}
  onChange={(e) => setDescription(e.target.value)}
  rows={4}
  isRequired
/>;

{
  /* RHF */
}
<TextAreaField
  name="description"
  control={control}
  rules={{ maxLength: { value: 500, message: 'Too long' } }}
  rows={4}
/>;
```

---

## CustomTab

Ant Design-style line tabs built on Radix Tab primitives. Items-based API with `TabItem[]`.

| Prop             | Type                    | Default          | Description                                |
| ---------------- | ----------------------- | ---------------- | ------------------------------------------ |
| items            | `TabItem[]`             | —                | **Required.** Tab definitions (see below). |
| defaultActiveKey | string                  | first item's key | Default active tab (uncontrolled).         |
| activeKey        | string                  | —                | Controlled active tab key.                 |
| onTabChange      | `(key: string) => void` | —                | Called when the active tab changes.        |
| className        | string                  | —                | Class for the root container.              |
| tabBarClassName  | string                  | —                | Class for the tab bar (trigger list).      |
| contentClassName | string                  | —                | Class for each tab content panel.          |

**TabItem:**

| Field    | Type      | Description                          |
| -------- | --------- | ------------------------------------ |
| key      | string    | **Required.** Unique tab identifier. |
| label    | ReactNode | **Required.** Tab trigger label.     |
| icon     | ReactNode | Optional icon before label.          |
| disabled | boolean   | Disables the tab trigger.            |
| children | ReactNode | **Required.** Tab panel content.     |

**Example:**

```tsx
<CustomTab
  activeKey={activeTab}
  onTabChange={setActiveTab}
  items={[
    { key: 'general', label: 'General', icon: <Settings size={16} />, children: <GeneralTab /> },
    { key: 'voice', label: 'Voice', icon: <Volume2 size={16} />, children: <VoiceTab /> },
  ]}
/>
```

---

## SearchableSelect

Popover-based combobox with built-in search, keyboard navigation, and custom item rendering. Use when options need rich JSX (avatars, badges, descriptions) or when the list is long enough to warrant filtering.

### Props

| Prop                | Type                                            | Default                | Description                                                  |
| ------------------- | ----------------------------------------------- | ---------------------- | ------------------------------------------------------------ |
| name                | string                                          | —                      | **Required.** Input name and id.                             |
| options             | `T[]` (extends `SearchableSelectOption`)        | —                      | **Required.** `{ value, label, ...extra }[]`.                |
| value               | string                                          | —                      | Controlled value.                                            |
| onValueChange       | `(value: string) => void`                       | —                      | Called when selection changes.                               |
| placeholder         | string                                          | `'Select an option'`   | Trigger placeholder.                                         |
| searchPlaceholder   | string                                          | `'Search...'`          | Search input placeholder.                                    |
| label               | string                                          | —                      | Label text above the trigger.                                |
| isRequired          | boolean                                         | `false`                | Shows asterisk on label.                                     |
| loading             | boolean                                         | `false`                | Shows skeleton.                                              |
| disabled            | boolean                                         | `false`                | Disables the trigger.                                        |
| error               | boolean                                         | `false`                | Destructive border + ring.                                   |
| helperText          | string                                          | —                      | Small text below trigger.                                    |
| renderOption        | `(option: T, isSelected: boolean) => ReactNode` | —                      | Custom item renderer. Falls back to plain text + check icon. |
| renderSelectedValue | `(option: T) => ReactNode`                      | —                      | Custom trigger display. Falls back to label.                 |
| filterFn            | `(option: T, query: string) => boolean`         | case-insensitive label | Custom search filter.                                        |
| emptyMessage        | string                                          | `'No results found.'`  | Shown when no options match the search.                      |
| className           | string                                          | —                      | Class for the outer wrapper.                                 |

**SearchableSelectOption:** `{ value: string; label: string; disabled?: boolean }`

### Example

```tsx
<SearchableSelect
  name="voice"
  options={voiceOptions}
  value={selectedVoice}
  onValueChange={setSelectedVoice}
  placeholder="Select a voice"
  searchPlaceholder="Search voices..."
  renderOption={(opt, isSelected) => (
    <div className="flex items-center gap-2">
      <Avatar name={opt.name} />
      <span>{opt.label}</span>
      {isSelected && <CheckIcon className="size-4" />}
    </div>
  )}
  renderSelectedValue={(opt) => <span>{opt.label}</span>}
  filterFn={(opt, q) => opt.label.toLowerCase().includes(q.toLowerCase())}
/>
```

### Do's and Don'ts

- **Do** use `SearchableSelect` when options need custom rendering (avatars, badges, descriptions).
- **Do** use `SelectInput` for simple text-only dropdowns with few options.
- **Do** provide `renderOption` with a check indicator for the selected item.
- **Don't** use `SearchableSelect` if options are plain `{ value, label }` — use `SelectInput` instead.

---

## MultiSelectField

Multi-value selection field. Two modes: checkbox-based (when `options` provided) or freeform tag input (when no `options`). Uses shadcn `Checkbox`, `Input`, and `Label`. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop           | Type                        | Default        | Description                                              |
| -------------- | --------------------------- | -------------- | -------------------------------------------------------- |
| name           | string                      | —              | **Required.** Field name.                                |
| options        | `MultiSelectOption[]`       | —              | `{ value, label }[]`. If omitted, renders freeform tags. |
| value          | `string[]`                  | `[]`           | Currently selected values.                               |
| onChange       | `(value: string[]) => void` | —              | Called when selection changes.                           |
| placeholder    | string                      | `'Add <name>'` | Placeholder for tag input (no-options mode).             |
| label          | string                      | —              | Label text above the field.                              |
| isRequired     | boolean                     | `false`        | Shows asterisk on label.                                 |
| loading        | boolean                     | `false`        | Shows skeleton.                                          |
| disabled       | boolean                     | `false`        | Disables all inputs.                                     |
| error          | boolean                     | `false`        | Destructive border/ring.                                 |
| helperText     | string                      | —              | Small text below field.                                  |
| labelClassName | string                      | —              | Class for the label.                                     |
| className      | string                      | —              | Class for the outer wrapper.                             |

### RHF mode (with `control`)

Error state and helperText are auto-derived from `fieldState`.

| Prop                                                       | Type                        | Default | Description                   |
| ---------------------------------------------------------- | --------------------------- | ------- | ----------------------------- |
| name                                                       | string                      | —       | **Required.** RHF field name. |
| control                                                    | `Control<any>`              | —       | **Required.** RHF `control`.  |
| rules                                                      | `RegisterOptions`           | —       | RHF validation rules.         |
| onChange                                                   | `(value: string[]) => void` | —       | Side-effect callback.         |
| + plain MultiSelectField props (minus `value`, `onChange`) |                             |         | Forwarded.                    |

**MultiSelectOption:** `{ value: string; label: string }`

### Examples

```tsx
{
  /* Checkbox mode (with options) */
}
<MultiSelectField
  name="languages"
  options={[
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Spanish' },
  ]}
  value={selectedLangs}
  onChange={setSelectedLangs}
/>;

{
  /* Tag input mode (no options) */
}
<MultiSelectField name="tags" value={tags} onChange={setTags} placeholder="Add a tag" />;

{
  /* RHF */
}
<MultiSelectField
  name="languages"
  control={control}
  options={langOptions}
  onChange={(v) => handleChange('languages', v)}
/>;
```

---

## SliderField

Range slider with min/max/current value labels. Wraps shadcn `Slider`. **Unified component** — when a `control` prop is provided, it automatically wraps in an RHF `Controller`.

### Plain mode (no `control`)

| Prop           | Type                      | Default | Description                         |
| -------------- | ------------------------- | ------- | ----------------------------------- |
| name           | string                    | —       | **Required.** Field name.           |
| value          | number                    | `min`   | Current slider value.               |
| onValueChange  | `(value: number) => void` | —       | Called when slider value changes.   |
| min            | number                    | `0`     | Minimum value.                      |
| max            | number                    | `100`   | Maximum value.                      |
| step           | number                    | `1`     | Step increment.                     |
| label          | string                    | —       | Label text above slider.            |
| isRequired     | boolean                   | `false` | Shows asterisk on label.            |
| loading        | boolean                   | `false` | Shows skeleton.                     |
| disabled       | boolean                   | `false` | Disables the slider.                |
| error          | boolean                   | `false` | Error state.                        |
| helperText     | string                    | —       | Small text below slider.            |
| showLabels     | boolean                   | `true`  | Shows min/current/max labels below. |
| labelClassName | string                    | —       | Class for the label.                |
| className      | string                    | —       | Class for the outer wrapper.        |

### RHF mode (with `control`)

Error state and helperText are auto-derived from `fieldState`.

| Prop                                                       | Type                      | Default | Description                   |
| ---------------------------------------------------------- | ------------------------- | ------- | ----------------------------- |
| name                                                       | string                    | —       | **Required.** RHF field name. |
| control                                                    | `Control<any>`            | —       | **Required.** RHF `control`.  |
| rules                                                      | `RegisterOptions`         | —       | RHF validation rules.         |
| onValueChange                                              | `(value: number) => void` | —       | Side-effect callback.         |
| + plain SliderField props (minus `value`, `onValueChange`) |                           |         | Forwarded.                    |

### Examples

```tsx
{
  /* Plain */
}
<SliderField name="temperature" value={temp} onValueChange={setTemp} min={0} max={2} step={0.1} />;

{
  /* RHF */
}
<SliderField
  name="temperature"
  control={control}
  min={0}
  max={2}
  step={0.1}
  onValueChange={(v) => handleChange('temperature', v)}
/>;
```

---

## Unified Form Components — How It Works

All form-field components (`TextInput`, `CheckboxField`, `RadioGroupField`, `SelectInput`, `TextAreaField`, `MultiSelectField`, `SliderField`) follow the same **unified pattern**: a single component that acts as both a plain input and an RHF-connected input based on whether the `control` prop is provided.

### Pattern

```tsx
{
  /* Plain usage — standard controlled/uncontrolled component */
}
<TextInput name="email" value={email} onChange={(e) => setEmail(e.target.value)} />;

{
  /* RHF usage — pass control to activate Controller integration */
}
<TextInput name="email" control={control} rules={{ required: 'Email is required' }} />;
```

### How it works internally

1. Each component checks for the presence of a `control` prop
2. **Without `control`** → renders the plain input with standard React props (`value`, `onChange`, etc.)
3. **With `control`** → wraps the plain input in an RHF `Controller`, auto-connecting `field.value`, `field.onChange`, `field.onBlur`, and deriving `error`/`helperText` from `fieldState`

### Migration from Form\* components

The previous separate `Form*` wrapper components (`FormTextInput`, `FormSelectInput`, etc.) have been merged into their base components. To migrate:

| Before                                         | After                                      |
| ---------------------------------------------- | ------------------------------------------ |
| `<FormTextInput name="x" control={c} />`       | `<TextInput name="x" control={c} />`       |
| `<FormSelectInput name="x" control={c} />`     | `<SelectInput name="x" control={c} />`     |
| `<FormTextAreaField name="x" control={c} />`   | `<TextAreaField name="x" control={c} />`   |
| `<FormCheckboxField id="x" control={c} />`     | `<CheckboxField id="x" control={c} />`     |
| `<FormRadioGroupField name="x" control={c} />` | `<RadioGroupField name="x" control={c} />` |

### Validation approaches

- **Agent form:** Uses `rules` prop (RHF built-in validation), e.g. `rules={{ required: 'Name is required' }}`
- **Auth forms:** Uses `zodResolver(schema)` on `useForm` — Zod schemas in `src/schemas/auth.ts` handle validation; no `rules` prop needed

---

## Exports from `@/components/shared`

- **Components:** `ActionMenu`, `CheckboxField`, `CustomButton`, `CustomLink`, `CustomModal`, `CustomTab`, `CustomTable`, `Divider`, `Form`, `Logo`, `MultiSelectField`, `RadioGroupField`, `SearchableSelect`, `SelectInput`, `SliderField`, `TextAreaField`, `TextInput`
- **Types:** `ActionMenuProps`, `CheckboxFieldBaseProps`, `CustomModalProps`, `CustomTableColumn`, `CustomTablePagination`, `CustomTableProps`, `FormCheckboxFieldProps`, `FormMultiSelectFieldProps`, `FormRadioGroupFieldProps`, `FormSelectInputProps`, `FormSliderFieldProps`, `FormTextAreaFieldProps`, `FormTextInputProps`, `MultiSelectFieldBaseProps`, `MultiSelectOption`, `RadioGroupOption`, `SearchableSelectOption`, `SelectInputBaseProps`, `SelectOption`, `SliderFieldBaseProps`, `TabItem`, `TextAreaFieldBaseProps`, `TextInputBaseProps`

---

_When adding or changing shared components, update this file so that docs stay the single source of truth and token usage stays low._

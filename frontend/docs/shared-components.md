# Shared Components Reference

Single source of truth for `@/components/shared` components. Use this file to understand APIs and usage without reading each component file (reduces token usage).

**Import from:** `@/components/shared` (barrel) or `@/components/shared/<ComponentName>`.

---

## CustomTable

Reusable data table built on shadcn `Table` primitives. API follows Ant Design Table conventions (`columns`, `dataSource`, `rowKey`, `render`, `pagination`). Includes built-in client-side search, sorting, pagination, loading skeleton, and empty state.

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

Wraps shadcn `Input` + `Label`. Supports password visibility toggle.

| Prop                     | Type      | Default  | Description                                                    |
| ------------------------ | --------- | -------- | -------------------------------------------------------------- |
| name                     | string    | —        | **Required.** Input name and id.                               |
| type                     | string    | `'text'` | Input type. `'password'` shows show/hide toggle.               |
| label                    | string    | —        | Label text above input.                                        |
| isRequired               | boolean   | `false`  | Shows asterisk, sets aria.                                     |
| loading                  | boolean   | `false`  | Shows skeleton instead of input.                               |
| error                    | boolean   | `false`  | Destructive border + ring.                                     |
| helperText               | string    | —        | Small text below input.                                        |
| labelClassName           | string    | —        | Class for the label.                                           |
| className                | string    | —        | Class for the input.                                           |
| leftIcon                 | ReactNode | —        | Optional icon on the left (e.g. Search). Adds `pl-9` to input. |
| + all native input props |           |          | placeholder, value, defaultValue, onChange, disabled, etc.     |

**Example:**

```tsx
<TextInput name="email" type="email" label="Email" placeholder="Enter email" isRequired />
<TextInput name="password" type="password" label="Password" isRequired error={!!err} helperText={err} />
<TextInput name="table-search" placeholder="Search..." leftIcon={<Search />} value={q} onChange={(e) => setQ(e.target.value)} />
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

Simple form wrapper that collects native input values and calls `onFinish(values)` on submit. No validation—just `FormData` → object.

| Prop         | Type                                  | Default      | Description                                        |
| ------------ | ------------------------------------- | ------------ | -------------------------------------------------- |
| children     | ReactNode                             | —            | Form content (inputs must have `name`).            |
| onFinish     | (values: Record<string, any>) => void | —            | **Required.** Called with key-value map from form. |
| layout       | `'horizontal' \| 'vertical'`          | `'vertical'` | Flex direction.                                    |
| autoComplete | string                                | `'off'`      | Form autocomplete.                                 |
| className    | string                                | —            | Applied to `<form>`.                               |

**Example:**

```tsx
<Form onFinish={(values) => login(values.email, values.password)} layout="vertical">
  <TextInput name="email" label="Email" />
  <TextInput name="password" type="password" label="Password" />
  <CustomButton type="primary" htmlType="submit">
    Submit
  </CustomButton>
</Form>
```

---

## CheckboxField

Checkbox + label + optional helper/error. Uses shadcn `Checkbox` and `Label`.

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

**Example:**

```tsx
<CheckboxField id="remember" label="Remember me" defaultChecked />
<CheckboxField id="terms" label="I agree" isRequired error={!!err} helperText={err} />
```

---

## RadioGroupField

Single-choice group. Uses shadcn `RadioGroup` + `RadioGroupItem` + `Label` per option.

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

**RadioGroupOption:** `{ value: string; label: string; disabled?: boolean }`

**Example:**

```tsx
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
/>
```

---

## Exports from `@/components/shared`

- **Components:** `CheckboxField`, `CustomButton`, `CustomLink`, `CustomModal`, `CustomTable`, `Form`, `Logo`, `RadioGroupField`, `TextInput`
- **Types:** `CustomModalProps`, `CustomTableColumn`, `CustomTablePagination`, `CustomTableProps`, `RadioGroupOption`

---

_When adding or changing shared components, update this file so that docs stay the single source of truth and token usage stays low._

---
name: shadcn-ui
description: Use shadcn/ui components correctly in React + Tailwind projects. Covers component usage patterns, theming with CSS variables, form handling with react-hook-form + zod, and complex components like data tables. Always install via yarn and follow shadcn/ui conventions.
version: 1.0.0
stack: React + Tailwind CSS + shadcn/ui
package-manager: yarn
---

This skill ensures correct, idiomatic usage of shadcn/ui when building React interfaces. shadcn/ui is NOT a traditional npm package — it copies component source code directly into your project. Always follow its conventions precisely.

---

## 1. What shadcn/ui Is (And Isn't)

- **NOT** an npm package you import from `shadcn/ui`
- **IS** a CLI that copies component source files into `./components/ui/`
- You OWN the component code — edit it freely
- Built on **Radix UI** primitives + **Tailwind CSS**
- Requires `tailwindcss`, `tailwindcss-animate`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`

### Install a component
```bash
# Always use yarn
yarn dlx shadcn@latest add button
yarn dlx shadcn@latest add card input label badge
yarn dlx shadcn@latest add dialog sheet drawer
yarn dlx shadcn@latest add form        # includes react-hook-form integration
yarn dlx shadcn@latest add data-table  # includes tanstack/react-table
```

### Init (new project)
```bash
yarn dlx shadcn@latest init
```

---

## 2. Project Structure

After init, shadcn/ui creates:
```
your-app/
├── components/
│   └── ui/              ← shadcn/ui components live here (DO NOT import from npm)
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       └── ...
├── lib/
│   └── utils.ts         ← cn() utility lives here
├── tailwind.config.ts
└── globals.css          ← CSS variables / theme tokens
```

### The `cn()` utility — use it everywhere
```ts
// lib/utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

```tsx
// Always use cn() for conditional/merged Tailwind classes
<div className={cn("base-class", isActive && "active-class", className)}>
```

---

## 3. Theming & CSS Variables

shadcn/ui uses CSS variables for all colors — NEVER hardcode color values.

### globals.css structure
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Light theme */
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;

    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;

    --popover: 0 0% 100%;
    --popover-foreground: 240 10% 3.9%;

    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;

    --secondary: 240 4.8% 95.9%;
    --secondary-foreground: 240 5.9% 10%;

    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;

    --accent: 240 4.8% 95.9%;
    --accent-foreground: 240 5.9% 10%;

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;

    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --ring: 240 5.9% 10%;

    --radius: 0.5rem;
  }

  .dark {
    /* Dark theme */
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 240 10% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 240 3.7% 15.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }
}
```

### Customizing the theme
Change `--primary` to match your brand color:
```css
:root {
  /* Acid yellow brand */
  --primary: 66 100% 64%;
  --primary-foreground: 0 0% 0%;

  /* Custom radius */
  --radius: 0.75rem;
}
```

### Using theme variables in Tailwind
```tsx
// Use semantic Tailwind classes that map to CSS variables
<div className="bg-background text-foreground">
<div className="bg-card text-card-foreground border border-border">
<button className="bg-primary text-primary-foreground hover:bg-primary/90">
<p className="text-muted-foreground">
<div className="bg-secondary text-secondary-foreground">
```

### Dark mode setup
```tsx
// Use next-themes or class strategy
// tailwind.config.ts
export default {
  darkMode: ["class"],
  // ...
}

// Toggle dark mode by adding/removing 'dark' class on <html>
```

---

## 4. Component Usage Patterns

### Button
```tsx
import { Button } from "@/components/ui/button"

// Variants: default, destructive, outline, secondary, ghost, link
// Sizes: default, sm, lg, icon

<Button>Default</Button>
<Button variant="outline">Outline</Button>
<Button variant="destructive">Delete</Button>
<Button variant="ghost" size="icon" aria-label="Settings">
  <SettingsIcon className="h-4 w-4" />
</Button>
<Button disabled>Disabled</Button>
<Button>
  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
  Loading...
</Button>
```

### Card
```tsx
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description goes here.</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content</p>
  </CardContent>
  <CardFooter className="flex justify-between">
    <Button variant="outline">Cancel</Button>
    <Button>Continue</Button>
  </CardFooter>
</Card>
```

### Dialog (Modal)
```tsx
import {
  Dialog, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle, DialogTrigger
} from "@/components/ui/dialog"

<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[425px]">
    <DialogHeader>
      <DialogTitle>Edit Profile</DialogTitle>
      <DialogDescription>Make changes to your profile here.</DialogDescription>
    </DialogHeader>
    {/* content */}
    <DialogFooter>
      <Button type="submit">Save changes</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Sheet (Side panel)
```tsx
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"

<Sheet>
  <SheetTrigger asChild>
    <Button variant="outline">Open Sheet</Button>
  </SheetTrigger>
  <SheetContent side="right"> {/* side: top | right | bottom | left */}
    <SheetHeader>
      <SheetTitle>Edit Profile</SheetTitle>
      <SheetDescription>Make changes to your profile.</SheetDescription>
    </SheetHeader>
    {/* content */}
  </SheetContent>
</Sheet>
```

### Dropdown Menu
```tsx
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu"

<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="outline">Options</Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuLabel>My Account</DropdownMenuLabel>
    <DropdownMenuSeparator />
    <DropdownMenuItem>Profile</DropdownMenuItem>
    <DropdownMenuItem>Settings</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem className="text-destructive">Log out</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

### Toast (Sonner — recommended)
```bash
yarn dlx shadcn@latest add sonner
```
```tsx
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"

// In layout.tsx
<Toaster />

// Trigger toasts anywhere
toast("Event has been created.")
toast.success("Profile updated!")
toast.error("Something went wrong.")
toast.promise(saveData(), {
  loading: 'Saving...',
  success: 'Saved!',
  error: 'Error saving.',
})
```

### Select
```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

<Select onValueChange={setValue} defaultValue={value}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Select a fruit" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="apple">Apple</SelectItem>
    <SelectItem value="banana">Banana</SelectItem>
    <SelectItem value="orange">Orange</SelectItem>
  </SelectContent>
</Select>
```

### Tabs
```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

<Tabs defaultValue="account">
  <TabsList>
    <TabsTrigger value="account">Account</TabsTrigger>
    <TabsTrigger value="password">Password</TabsTrigger>
  </TabsList>
  <TabsContent value="account">Account settings</TabsContent>
  <TabsContent value="password">Change password</TabsContent>
</Tabs>
```

### Badge
```tsx
import { Badge } from "@/components/ui/badge"

// Variants: default, secondary, destructive, outline
<Badge>New</Badge>
<Badge variant="secondary">Beta</Badge>
<Badge variant="destructive">Deprecated</Badge>
<Badge variant="outline">Draft</Badge>
```

### Avatar
```tsx
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

<Avatar>
  <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
  <AvatarFallback>CN</AvatarFallback>
</Avatar>
```

### Skeleton (Loading state)
```tsx
import { Skeleton } from "@/components/ui/skeleton"

<div className="flex items-center space-x-4">
  <Skeleton className="h-12 w-12 rounded-full" />
  <div className="space-y-2">
    <Skeleton className="h-4 w-[250px]" />
    <Skeleton className="h-4 w-[200px]" />
  </div>
</div>
```

---

## 5. Form Handling (react-hook-form + zod)

### Install
```bash
yarn add react-hook-form zod @hookform/resolvers
yarn dlx shadcn@latest add form input label textarea select checkbox
```

### Complete Form Pattern
```tsx
"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import {
  Form, FormControl, FormDescription,
  FormField, FormItem, FormLabel, FormMessage
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"

// 1. Define schema
const formSchema = z.object({
  username: z.string()
    .min(2, { message: "Username must be at least 2 characters." })
    .max(50, { message: "Username must be under 50 characters." }),
  email: z.string().email({ message: "Invalid email address." }),
  age: z.coerce.number()
    .min(18, { message: "Must be at least 18." })
    .max(120),
})

type FormValues = z.infer<typeof formSchema>

// 2. Build form component
export function ProfileForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: "",
      email: "",
      age: undefined,
    },
  })

  const { isSubmitting } = form.formState

  async function onSubmit(values: FormValues) {
    try {
      await saveProfile(values)
      toast.success("Profile saved!")
      form.reset()
    } catch {
      toast.error("Something went wrong.")
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input placeholder="shadcn" {...field} />
              </FormControl>
              <FormDescription>Your public display name.</FormDescription>
              <FormMessage /> {/* auto renders zod error */}
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="you@example.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
          ) : "Save Profile"}
        </Button>

      </form>
    </Form>
  )
}
```

### Select inside Form
```tsx
<FormField
  control={form.control}
  name="role"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Role</FormLabel>
      <Select onValueChange={field.onChange} defaultValue={field.value}>
        <FormControl>
          <SelectTrigger>
            <SelectValue placeholder="Select a role" />
          </SelectTrigger>
        </FormControl>
        <SelectContent>
          <SelectItem value="admin">Admin</SelectItem>
          <SelectItem value="editor">Editor</SelectItem>
          <SelectItem value="viewer">Viewer</SelectItem>
        </SelectContent>
      </Select>
      <FormMessage />
    </FormItem>
  )}
/>
```

### Checkbox inside Form
```tsx
<FormField
  control={form.control}
  name="acceptTerms"
  render={({ field }) => (
    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
      <FormControl>
        <Checkbox checked={field.value} onCheckedChange={field.onChange} />
      </FormControl>
      <div className="space-y-1 leading-none">
        <FormLabel>Accept terms and conditions</FormLabel>
        <FormMessage />
      </div>
    </FormItem>
  )}
/>
```

### Common Zod Patterns
```ts
const schema = z.object({
  // String validations
  name: z.string().min(1, "Required").max(100),
  slug: z.string().regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers, hyphens"),
  url: z.string().url("Must be a valid URL").optional(),

  // Number
  price: z.coerce.number().positive("Must be positive").multipleOf(0.01),

  // Enum
  status: z.enum(["draft", "published", "archived"]),

  // Optional with default
  bio: z.string().max(500).optional().default(""),

  // Conditional
  phone: z.string().optional().refine(
    (val) => !val || /^\+?[1-9]\d{1,14}$/.test(val),
    "Invalid phone number"
  ),

  // Passwords match
  password: z.string().min(8),
  confirmPassword: z.string(),
}).refine(
  (data) => data.password === data.confirmPassword,
  { message: "Passwords don't match", path: ["confirmPassword"] }
)
```

---

## 6. Data Tables (TanStack Table)

### Install
```bash
yarn add @tanstack/react-table
yarn dlx shadcn@latest add table
```

### Full Data Table Pattern
```tsx
"use client"

import { useState } from "react"
import {
  ColumnDef, ColumnFiltersState, SortingState, VisibilityState,
  flexRender, getCoreRowModel, getFilteredRowModel,
  getPaginationRowModel, getSortedRowModel, useReactTable,
} from "@tanstack/react-table"
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu, DropdownMenuCheckboxItem,
  DropdownMenuContent, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu"
import { ArrowUpDown, ChevronDown } from "lucide-react"

// 1. Define your data type
type Payment = {
  id: string
  amount: number
  status: "pending" | "processing" | "success" | "failed"
  email: string
  createdAt: string
}

// 2. Define columns
const columns: ColumnDef<Payment>[] = [
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.getValue<string>("status")
      const variantMap = {
        success: "default",
        failed: "destructive",
        pending: "secondary",
        processing: "outline",
      } as const
      return <Badge variant={variantMap[status as keyof typeof variantMap]}>{status}</Badge>
    },
  },
  {
    accessorKey: "email",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Email <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "amount",
    header: () => <div className="text-right">Amount</div>,
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue("amount"))
      const formatted = new Intl.NumberFormat("en-US", {
        style: "currency", currency: "USD"
      }).format(amount)
      return <div className="text-right font-medium">{formatted}</div>
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const payment = row.original
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Actions">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => navigator.clipboard.writeText(payment.id)}>
              Copy ID
            </DropdownMenuItem>
            <DropdownMenuItem>View details</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
]

// 3. DataTable component
export function DataTable({ data }: { data: Payment[] }) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { sorting, columnFilters, columnVisibility },
  })

  return (
    <div className="w-full space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter emails..."
          value={(table.getColumn("email")?.getFilterValue() as string) ?? ""}
          onChange={(e) => table.getColumn("email")?.setFilterValue(e.target.value)}
          className="max-w-sm"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="ml-auto">
              Columns <ChevronDown className="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {table.getAllColumns()
              .filter((col) => col.getCanHide())
              .map((col) => (
                <DropdownMenuCheckboxItem
                  key={col.id}
                  checked={col.getIsVisible()}
                  onCheckedChange={(val) => col.toggleVisibility(!!val)}
                >
                  {col.id}
                </DropdownMenuCheckboxItem>
              ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Table */}
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {table.getFilteredRowModel().rows.length} row(s)
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline" size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            Previous
          </Button>
          <Button
            variant="outline" size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

## 7. Common Patterns & Best Practices

### Composing components
```tsx
// Use asChild to pass behavior to child elements (avoids wrapping divs)
<DialogTrigger asChild>
  <Button>Open</Button>   // Button gets trigger behavior, no extra wrapper
</DialogTrigger>

<TooltipTrigger asChild>
  <Button variant="ghost" size="icon">
    <InfoIcon className="h-4 w-4" />
  </Button>
</TooltipTrigger>
```

### Extending components
```tsx
// Add custom variants to Button without modifying the original
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Use buttonVariants for non-button elements that look like buttons
<Link
  href="/dashboard"
  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
>
  Dashboard
</Link>
```

### Controlled vs Uncontrolled
```tsx
// shadcn/ui supports both — prefer controlled for complex state

// Uncontrolled (simple use cases)
<Dialog>...</Dialog>

// Controlled (programmatic open/close)
const [open, setOpen] = useState(false)
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>
    <Button onClick={() => setOpen(false)}>Close</Button>
  </DialogContent>
</Dialog>
```

### Loading & async states
```tsx
// Always handle loading states in buttons
const [isPending, startTransition] = useTransition()

<Button
  onClick={() => startTransition(async () => { await action() })}
  disabled={isPending}
>
  {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
  {isPending ? "Saving..." : "Save"}
</Button>
```

---

## 8. Quality Checklist

Before delivering any shadcn/ui interface:

**Setup**
- [ ] Components installed via `yarn dlx shadcn@latest add`, NOT imported from npm
- [ ] `cn()` utility used for all conditional class merging
- [ ] CSS variables defined in `globals.css`

**Components**
- [ ] `asChild` used where appropriate (no unnecessary wrapper divs)
- [ ] All dialogs/sheets are controlled or have proper triggers
- [ ] Icon-only buttons have `aria-label`

**Forms**
- [ ] Schema defined with zod before building form
- [ ] `FormMessage` included in every `FormField` for error display
- [ ] Submit button shows loading state during submission
- [ ] Errors handled with toast notifications

**Data Tables**
- [ ] Loading skeleton shown while data fetches
- [ ] Empty state handled ("No results")
- [ ] Pagination controls disabled when at first/last page

**Theme**
- [ ] Only semantic color classes used (`bg-background`, `text-foreground`, etc.)
- [ ] No hardcoded hex values in component classes
- [ ] Dark mode tested

---

Remember: shadcn/ui components are starting points, not constraints. You own the code — customize freely while keeping Radix UI accessibility primitives intact.

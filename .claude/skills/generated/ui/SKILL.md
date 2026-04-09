---
name: ui
description: "Skill for the Ui area of tone. 94 symbols across 48 files."
---

# Ui

94 symbols | 48 files | Cohesion: 96%

## When to Use

- Working with code in `frontend/`
- Understanding how cn, GoogleIcon, ProfileMenu work
- Modifying ui-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/src/components/ui/table.tsx` | alignClass, Table, TableHeader, TableBody, TableFooter (+5) |
| `frontend/src/components/ui/dropdown-menu.tsx` | DropdownMenuContent, DropdownMenuItem, DropdownMenuCheckboxItem, DropdownMenuRadioItem, DropdownMenuLabel (+4) |
| `frontend/src/components/ui/select.tsx` | SelectTrigger, SelectContent, SelectLabel, SelectItem, SelectSeparator (+2) |
| `frontend/src/components/ui/card.tsx` | Card, CardHeader, CardTitle, CardDescription, CardAction (+2) |
| `frontend/src/components/ui/sheet.tsx` | SheetOverlay, SheetContent, SheetHeader, SheetFooter, SheetTitle (+1) |
| `frontend/src/components/ui/dialog.tsx` | DialogOverlay, DialogContent, DialogHeader, DialogFooter, DialogTitle (+1) |
| `frontend/src/components/ui/tabs.tsx` | Tabs, TabsList, TabsTrigger, TabsContent |
| `frontend/src/components/shared/SearchableSelect.tsx` | Skeleton, SearchableSelectInner |
| `frontend/src/components/agents/AssignPhoneNumberModal.tsx` | AssignPhoneNumberModal, toggleNumber |
| `frontend/src/components/shared/SidebarComponent/SidebarNav.tsx` | SidebarNav, isActive |

## Entry Points

Start here when exploring this area:

- **`cn`** (Function) — `frontend/src/utils/cn.ts:3`
- **`GoogleIcon`** (Function) — `frontend/src/components/icons/google.tsx:6`
- **`ProfileMenu`** (Function) — `frontend/src/components/shared/userMenu.tsx:30`
- **`ThemeToggle`** (Function) — `frontend/src/components/shared/ThemeToggle.tsx:8`
- **`Form`** (Function) — `frontend/src/components/shared/Form.tsx:13`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `cn` | Function | `frontend/src/utils/cn.ts` | 3 |
| `GoogleIcon` | Function | `frontend/src/components/icons/google.tsx` | 6 |
| `ProfileMenu` | Function | `frontend/src/components/shared/userMenu.tsx` | 30 |
| `ThemeToggle` | Function | `frontend/src/components/shared/ThemeToggle.tsx` | 8 |
| `Form` | Function | `frontend/src/components/shared/Form.tsx` | 13 |
| `AssignPhoneNumberModal` | Function | `frontend/src/components/agents/AssignPhoneNumberModal.tsx` | 22 |
| `toggleNumber` | Function | `frontend/src/components/agents/AssignPhoneNumberModal.tsx` | 56 |
| `AgentTypeBadge` | Function | `frontend/src/components/agents/AgentTypeBadge.tsx` | 21 |
| `HomePage` | Function | `frontend/src/app/(dashboard)/home/page.tsx` | 127 |
| `SidebarOrganization` | Function | `frontend/src/components/shared/SidebarComponent/SidebarOrganization.tsx` | 13 |
| `SidebarNav` | Function | `frontend/src/components/shared/SidebarComponent/SidebarNav.tsx` | 13 |
| `isActive` | Function | `frontend/src/components/shared/SidebarComponent/SidebarNav.tsx` | 15 |
| `SidebarItemMenu` | Function | `frontend/src/components/shared/SidebarComponent/SidebarItemMenu.tsx` | 14 |
| `SidebarHeader` | Function | `frontend/src/components/shared/SidebarComponent/SidebarHeader.tsx` | 13 |
| `SidebarContent` | Function | `frontend/src/components/shared/SidebarComponent/SidebarContent.tsx` | 18 |
| `syncState` | Function | `frontend/src/components/agents/agent-form/promptPage.tsx` | 108 |
| `StatCard` | Function | `frontend/src/components/call-history/metrics/StatCard.tsx` | 11 |
| `BarChart` | Function | `frontend/src/components/call-history/metrics/BarChart.tsx` | 10 |
| `TooltipContent` | Function | `frontend/src/components/ui/tooltip.tsx` | 28 |
| `Textarea` | Function | `frontend/src/components/ui/textarea.tsx` | 4 |

## How to Explore

1. `gitnexus_context({name: "cn"})` — see callers and callees
2. `gitnexus_query({query: "ui"})` — find related execution flows
3. Read key files listed above for implementation details

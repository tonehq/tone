# Feature Doc: Settings (Landing / Overview)

Feature documentation for the Settings landing page at `/settings`. Used by
`/generate-tests settings` (or `--docs e2e/ux_flow_docs/settings.md`) to ensure all
user cases are covered.

The `/settings` page is the **overview hub** for the settings area: a single
column of grouped rows (Account → Workspace → Configuration) that each link
into a dedicated sub-page. It does NOT redirect; it renders an overview card
list. The settings area shares a `SidebarShell` rail (settings rail with a
"Back to app" primary slot + `AccountMenu` footer) used by every
`/settings/*` route through `settings/layout.tsx`.

Each sub-route owns its own feature doc:
- `/settings/profile` → see `user-settings.md`
- `/settings/organizations` → see `organizations.md`
- `/settings/members` → see `members.md`
- `/settings/model-providers` → see `model-providers.md`
- `/settings/integrations` → see `oauth-integrations.md` + `channels.md`

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/settings`
- **Wrapper**: `src/app/(dashboard)/settings/page.tsx`
- **Layout wrapper**: `src/app/(dashboard)/settings/layout.tsx`
- **Main component**: `src/components/settings/SettingsOverview.tsx`
- **Shared components**:
  - `src/components/layout/SidebarShell.tsx` (+ `isSidebarItemActive`)
  - `src/components/layout/AccountMenu.tsx`
  - `src/components/settings/navConfig.ts`
    (`SETTINGS_NAV_GROUPS`, `SETTINGS_NAV_ITEMS`, `SettingsNavItem`,
    `SettingsNavGroup`)
- **State**: `useAuthStore` selector `(s) => s.user` (Zustand), used for
  greeting name + initials
- **Auth required**: yes (no `tone_access_token` cookie → middleware redirect
  to `/auth/login?redirect=%2Fsettings`)

---

## User Stories

### US-1: Land on a clear overview hub

**As a** signed-in user, **I want to** see one tidy page that explains
every settings destination, **so that** I don't need to hunt through a
nested menu to find a section.

**Acceptance criteria**:

- [ ] URL `/settings` renders `SettingsOverview` (no redirect)
- [ ] Eyebrow text `Workspace settings` with a small primary-color dot
- [ ] Heading `Settings`
- [ ] Subtitle `Welcome back, <FirstName>. Manage your account, workspace, and connected services in one place.` — the `Welcome back, …` prefix is omitted if `user.first_name` is empty
- [ ] Three grouped sections render in this order: `Account` → `Workspace` → `Configuration`
- [ ] Each group shows an uppercase heading and a sub-caption

### US-2: Navigate into each sub-page

**As a** signed-in user, **I want** every row to be a single click into the corresponding settings page, **so that** I can edit a thing with minimal friction.

**Acceptance criteria**:

- [ ] Each row is an anchor `<Link>` with `href = item.href`
- [ ] Hovering a row updates the icon swatch and slides the chevron
- [ ] Rows render in order: User settings → Organizations → Members → Model Providers → Integrations
- [ ] The ungrouped `Overview` entry is NOT shown on the overview list

### US-3: Use the settings sidebar rail (desktop)

**As a** signed-in user on desktop, **I want** the settings rail to show every section plus a Back-to-app link, **so that** I can switch sections without returning to `/settings` first.

**Acceptance criteria**:

- [ ] On viewports `lg` and up, `SidebarShell` renders on the left
- [ ] Primary slot shows `Back to app` (`/home`) with `ArrowLeft`; collapsed view shows icon + tooltip
- [ ] Footer slot shows the `AccountMenu`
- [ ] Rail shares `sidebarCollapsed` state with the app sidebar via `useNavigation()`
- [ ] Active item uses `isSidebarItemActive`; `Overview` has `exact: true`

### US-4: Use the mobile top-bar sections nav

**As a** mobile user, **I want** a horizontal pill nav at the top of every settings page.

**Acceptance criteria**:

- [ ] Below `lg`, a sticky top bar shows a back arrow (→ `/home`), `Settings` text, and a scrollable pill nav
- [ ] Pills come from `SETTINGS_NAV_ITEMS`
- [ ] The active pill has `aria-current="page"` and uses accent styling

### US-5: Greet the user by name

**As a** signed-in user, **I want** my first name in the subtitle and an avatar swatch with my initials.

**Acceptance criteria**:

- [ ] Subtitle includes `Welcome back, <first_name>. ` when first_name is non-empty after trim
- [ ] Account swatch (sm+ only) shows initials via `getInitials(user.first_name, user.last_name)`, falling back to `U`
- [ ] Primary line is `<first> <last>` or literal `Your account` when both names empty
- [ ] Secondary line reads `View profile`
- [ ] Swatch is a `<Link href="/settings/profile">`

### US-6: Respect reduced motion

**As a** user with reduced-motion preferences, **I want** the staggered fade-in to be skipped.

**Acceptance criteria**:

- [ ] `useReducedMotion()` returns `true` → `staggerChildren` = 0 and `y` offset = 0
- [ ] Default → rows fade + translate from `y=8` to `y=0` with `staggerChildren: 0.04`

---

## UI Elements

| Element                  | Type     | Content / Label                                                       | Behavior                                          |
| ------------------------ | -------- | --------------------------------------------------------------------- | ------------------------------------------------- |
| Eyebrow                  | text     | `Workspace settings`                                                  | Static; primary-color dot + uppercase tracking    |
| Page heading             | h1       | `Settings`                                                            | Static                                            |
| Subtitle                 | p        | `Welcome back, <Name>. Manage your account, workspace, and connected services in one place.` | Greeting prefix conditional on `user.first_name` |
| Account swatch (desktop) | `<Link>` | initials + name + `View profile`                                      | Visible `sm:` and up; navigates to `/settings/profile` |
| Group section heading    | h2       | `ACCOUNT` / `WORKSPACE` / `CONFIGURATION`                             | Static                                            |
| Group caption            | p        | Per-group caption from `navConfig`                                    | Static                                            |
| Overview row             | `<Link>` | icon swatch + label + description + `ChevronRight`                    | Hover styling; chevron slides                     |
| Row — User settings      | `<Link>` | `UserCircle` icon                                                     | → `/settings/profile`                             |
| Row — Organizations      | `<Link>` | `Building2` icon                                                      | → `/settings/organizations`                       |
| Row — Members            | `<Link>` | `Users` icon                                                          | → `/settings/members`                             |
| Row — Model Providers    | `<Link>` | `Plug` icon                                                           | → `/settings/model-providers`                     |
| Row — Integrations       | `<Link>` | `Cable` icon                                                          | → `/settings/integrations`                        |
| Rail primary (desktop)   | `<Link>` | `Settings` + `Back to app`                                            | → `/home`                                         |
| Rail item                | `<Link>` | icon + label                                                          | `aria-current="page"` when active                 |
| Rail footer              | component | `AccountMenu`                                                        | Account menu actions                              |
| Mobile back arrow        | `<Link>` | `ArrowLeft` icon, `aria-label="Back to app"`                          | → `/home`                                         |
| Mobile header label      | span     | `Settings`                                                            | Static                                            |
| Mobile pill              | `<Link>` | icon + label                                                          | `aria-current="page"` when active                 |

---

## Input Specifications

The overview page has **no input fields**. The only interactive elements are anchor links and the rail collapse toggle.

| Control                | Type   | Validation | Behavior                                |
| ---------------------- | ------ | ---------- | --------------------------------------- |
| Row link (overview)    | `<a>`  | n/a        | Navigate to `item.href`                 |
| Rail item              | `<a>`  | n/a        | Navigate; active state per pathname     |
| Back-to-app (rail)     | `<a>`  | n/a        | Navigate to `/home`                     |
| Account swatch (desk.) | `<a>`  | n/a        | Navigate to `/settings/profile`         |
| Mobile back arrow      | `<a>`  | n/a        | Navigate to `/home`                     |
| Mobile pill            | `<a>`  | n/a        | Navigate; `aria-current` reflects state |
| Collapse handle        | button | n/a        | `useNavigation().toggleSidebar()`       |

---

## Navigation

| Trigger                          | Destination                              | Condition                              |
| -------------------------------- | ---------------------------------------- | -------------------------------------- |
| Visit `/settings` (auth'd)       | Renders `SettingsOverview`               | `tone_access_token` cookie present     |
| Visit `/settings` (no auth)      | `/auth/login?redirect=%2Fsettings`       | Middleware redirect                    |
| Click `User settings` row        | `/settings/profile`                      | Always                                 |
| Click `Organizations` row        | `/settings/organizations`                | Always                                 |
| Click `Members` row              | `/settings/members`                      | Always                                 |
| Click `Model Providers` row      | `/settings/model-providers`              | Always                                 |
| Click `Integrations` row         | `/settings/integrations`                 | Always                                 |
| Click account swatch (desktop)   | `/settings/profile`                      | Viewport `sm:` and up                  |
| Click rail `Back to app`         | `/home`                                  | Desktop rail                           |
| Click mobile back arrow          | `/home`                                  | Viewport < `lg`                        |
| Click rail/pill item             | Corresponding `/settings/*` URL          | Always                                 |
| Click rail collapse handle       | Same URL; rail width changes             | Desktop only                           |

---

## API Contracts

The `/settings` landing page itself makes **no API calls**. It reads the user object from the Zustand `useAuthStore` (hydrated from cookies set during login).

Sub-pages do call APIs; those contracts belong in their own feature docs.

For test setup without a live API, set the `tone_access_token`, `org_tenant_id`, and `login_data` cookies before navigation. The `login_data` cookie shape:

```json
{
  "id": "user-uuid",
  "email": "jane@acme.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "is_verified": true,
  "role": "owner"
}
```

If a background `GET /me` call is triggered by the app shell, error payloads follow the shared shape `{ "detail": "<string>" }`. Examples:

- 401: `{ "detail": "Could not validate credentials" }`
- 500: `{ "detail": "Internal Server Error" }`

> ⚠ unverified — confirm exact cookie name + JSON shape in `src/atoms/AuthAtom.tsx` / `src/stores/auth.ts`.

---

## Test Cases

---

### TC-HAPPY-001: Overview renders for a known user

**Preconditions**:
- Signed-in; `user.first_name = "Jane"`, `last_name = "Doe"`

**Action**:
1. Visit `/settings`

**Observation 1 — Header chrome**:
1. Eyebrow `Workspace settings` is visible
2. The page `h1` reads `Settings`
3. Subtitle starts with `Welcome back, Jane.`

**Observation 2 — Account swatch (desktop sm+)**:
1. Swatch initials read `JD`
2. Primary line equals `Jane Doe`
3. Secondary line equals `View profile`
4. Swatch is a `<Link>` with `href="/settings/profile"`

**Observation 3 — Three group sections render**:
1. Groups appear in order: `ACCOUNT` → `WORKSPACE` → `CONFIGURATION`
2. Each group has its own h2 heading and caption

**Observation 4 — No API call fires from this page**:
1. Zero XHRs originate from `/settings` itself (the overview page does not call any service)

---

### TC-HAPPY-002: Overview renders for an unnamed user

**Preconditions**: Signed-in; `user.first_name = ""`, `last_name = ""`.

**Action**:
1. Visit `/settings`

**Observation 1 — Greeting prefix dropped**:
1. Subtitle has no `Welcome back, …` prefix
2. Subtitle starts with `Manage your account, …`

**Observation 2 — Account swatch falls back**:
1. Initials read `U`
2. Primary line equals `Your account`

---

### TC-HAPPY-003: Each overview row navigates correctly

**Preconditions**: Signed-in.

**Action**:
1. Visit `/settings`
2. Click each of the 5 rows in order: User settings → Organizations → Members → Model Providers → Integrations
3. Return to `/settings` between clicks

**Observation 1 — URLs**:
1. URLs visited (in order): `/settings/profile`, `/settings/organizations`, `/settings/members`, `/settings/model-providers`, `/settings/integrations`

**Observation 2 — Client-side navigation**:
1. No full page reload occurs between rows (next/link)

---

### TC-HAPPY-004: Desktop rail renders Back-to-app + 6 items

**Preconditions**: Signed-in; viewport ≥ `lg`.

**Action**:
1. Visit `/settings`

**Observation 1 — Primary slot**:
1. The `Back to app` link is visible
2. Text shows `Settings` + `Back to app`

**Observation 2 — Six nav items**:
1. Rail items are: `Overview`, `User settings`, `Organizations`, `Members`, `Model Providers`, `Integrations`

**Observation 3 — Footer**:
1. The footer shows the `AccountMenu`

---

### TC-HAPPY-005: Mobile pill nav

**Preconditions**: Signed-in; viewport < `lg`.

**Action**:
1. Visit `/settings`

**Observation 1 — Top bar**:
1. A sticky top bar is visible
2. Back arrow has `aria-label="Back to app"`
3. The label `Settings` is visible

**Observation 2 — Pills**:
1. The pill nav has 6 items
2. The current-page pill has `aria-current="page"`

---

### TC-HAPPY-006: Active rail item updates on navigation

**Preconditions**: Signed-in; viewport ≥ `lg`.

**Action**:
1. Visit `/settings`
2. Click the rail `Members` item

**Observation 1 — URL + active state**:
1. URL becomes `/settings/members`
2. The rail `Members` item gains active styling / `aria-current="page"`
3. The `Overview` rail item loses active styling

---

### TC-HAPPY-007: Reduced motion is honored

**Preconditions**: Emulate `prefers-reduced-motion: reduce`.

**Action**:
1. Visit `/settings`

**Observation 1 — No motion**:
1. Rows are present without a staggered fade-in transform
2. No hidden initial frame visible to the user

---

### TC-HAPPY-008: Member (non-owner) can access the settings overview

**Preconditions**: Logged in as a `member`.

**Action**:
1. Visit `/settings`

**Observation 1 — Page renders**:
1. The overview page renders normally (no role gate on overview itself)

---

### TC-HAPPY-009: Overview omits the ungrouped `Overview` entry

**Action**:
1. Visit `/settings`

**Observation 1 — Overview not in landing list**:
1. The landing list does NOT contain the `Overview` row
2. Only the 5 grouped rows appear

---

### TC-HAPPY-010: Active-state Overview only on `/settings`

**Action**:
1. Visit `/settings`
2. Navigate to `/settings/profile` (via rail or row)

**Observation 1 — Active when on /settings**:
1. On `/settings` the `Overview` rail item is active

**Observation 2 — Inactive on a sub-route**:
1. On `/settings/profile` the `Overview` rail item is NOT active (it has `exact: true`)
2. Only `User settings` is highlighted

---

### TC-HAPPY-011: Deep link sub-route preserves rail

**Action**:
1. Open a fresh tab and paste `/settings/members` into the address bar

**Observation 1 — Rail correct without flash**:
1. The rail renders with `Members` active
2. There is no flash of `Overview` being active
3. The overview landing card list does NOT render

---

### TC-NAV-001: Click User settings row

**Action**:
1. Visit `/settings`
2. Click the `User settings` row

**Observation 1 — URL**: URL becomes `/settings/profile`.

**Observation 2 — Client-side**: no full page reload.

---

### TC-NAV-002: Click Organizations row

**Action**:
1. Visit `/settings`
2. Click the `Organizations` row

**Observation 1 — URL**: URL becomes `/settings/organizations`.

---

### TC-NAV-003: Click Members row

**Action**:
1. Visit `/settings`
2. Click the `Members` row

**Observation 1 — URL**: URL becomes `/settings/members`.

---

### TC-NAV-004: Click Model Providers row

**Action**:
1. Visit `/settings`
2. Click the `Model Providers` row

**Observation 1 — URL**: URL becomes `/settings/model-providers`.

---

### TC-NAV-005: Click Integrations row

**Action**:
1. Visit `/settings`
2. Click the `Integrations` row

**Observation 1 — URL**: URL becomes `/settings/integrations`.

---

### TC-NAV-006: Click rail Back to app

**Preconditions**: Viewport ≥ `lg`.

**Action**:
1. Visit `/settings`
2. Click the rail `Back to app` primary slot

**Observation 1 — URL**: URL becomes `/home`.

**Observation 2 — Sidebar**: the main app sidebar reappears.

---

### TC-NAV-007: Click account swatch on desktop

**Preconditions**: Viewport sm+.

**Action**:
1. Visit `/settings`
2. Click the account swatch (top-right)

**Observation 1 — URL**:
1. URL becomes `/settings/profile`
2. No flash of overview content during navigation

---

### TC-NAV-008: Mobile back arrow returns to /home

**Preconditions**: Viewport < `lg`.

**Action**:
1. Visit `/settings`
2. Tap the back arrow in the top bar

**Observation 1 — URL**: URL becomes `/home`.

---

### TC-NAV-009: Browser back from sub-route returns to overview

**Preconditions**: User on `/settings`; just navigated to `/settings/profile`.

**Action**:
1. Press the browser Back button

**Observation 1 — URL + active state**:
1. URL becomes `/settings`
2. The `Overview` rail item is active

---

### TC-NAV-010: Tab switch on mobile pill nav

**Preconditions**: Viewport < `lg`.

**Action**:
1. Visit `/settings`
2. Tap the `Members` pill

**Observation 1 — URL + aria-current**:
1. URL becomes `/settings/members`
2. The `Members` pill gains `aria-current="page"` after page change

---

### TC-NAV-011: Unauthenticated visit redirects to login

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/settings`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fsettings`
2. No `SettingsOverview` markup is rendered

---

### TC-NAV-012: Expired token redirects to login

**Preconditions**: `tone_access_token` cookie present but expired.

**Action**:
1. Visit `/settings`

**Observation 1 — Redirect + cookie cleanup**:
1. URL becomes `/auth/login?redirect=%2Fsettings`
2. The expired cookie is cleared by middleware (or on next /me 401)

---

### TC-NAV-013: Deep link sub-route without auth preserves redirect param

**Preconditions**: No auth cookie.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fprofile`
2. The settings rail is not rendered

---

### TC-LOADING-001: Slow /user/me hydrates greeting without flicker

**Action**:
1. Visit `/settings` with `GET /user/me` delayed by >3s

**Observation 1 — Eager render**:
1. The overview renders eagerly from the cookie's `login_data`

**Observation 2 — Hydrate without flicker**:
1. After the response lands, the greeting may update but does not flicker between blank and populated

---

### TC-ERROR-001: 401 background refresh degrades gracefully

**Action**:
1. Visit `/settings` with background `GET /user/me` mocked to return 401

**Observation 1 — Overview still renders**:
1. The overview renders with fallback user (initials `U`, no `Welcome back`)
2. No client-side crash

**Observation 2 — No toast on this page**:
1. Zero Sonner toasts appear on `/settings` itself

**API mock**: `GET /user/me` → `401 { "detail": "Could not validate credentials" }`.

---

### TC-ERROR-002: 500 background refresh degrades gracefully

**Action**:
1. Visit `/settings` with background `GET /user/me` mocked to return 500

**Observation 1 — Cached user fallback**:
1. The overview renders with the cached user from `login_data` cookie

**Observation 2 — No toast**:
1. Zero toasts appear on this page

**API mock**: `GET /user/me` → `500 { "detail": "Internal Server Error" }`.

---

### TC-ERROR-003: useAuthStore returns undefined

**Preconditions**: Cookie present but `login_data` failed to parse.

**Action**:
1. Visit `/settings`

**Observation 1 — Graceful fallback**:
1. Subtitle omits `Welcome back, …`
2. Account swatch initials = `U`
3. The rest of the overview renders normally

---

### TC-ERROR-004: Rail link to a 5xx page

**Preconditions**: Signed-in; the members API returns 500.

**Action**:
1. Visit `/settings`
2. Click the rail `Members` item

**Observation 1 — Navigation still succeeds**:
1. URL becomes `/settings/members`
2. The failure surfaces on `/settings/members`, NOT on `/settings`
3. The rail's active state still reflects `Members`

---

### TC-EDGE-001: `first_name` is whitespace only

**Preconditions**: `user.first_name = "   "`.

**Action**:
1. Visit `/settings`

**Observation 1 — Treated as empty**:
1. Subtitle has no `Welcome back, …` prefix (post-trim short-circuit)

---

### TC-EDGE-002: `last_name` missing but `first_name` present

**Preconditions**: `user.first_name = "Jane"`, `user.last_name = ""`.

**Action**:
1. Visit `/settings`

**Observation 1 — Initials safe**:
1. Initials use just `J`
2. No crash from `getInitials`

---

### TC-EDGE-003: Account swatch hidden below sm

**Preconditions**: Viewport < `sm`.

**Action**:
1. Visit `/settings`

**Observation 1 — Swatch hidden**:
1. The desktop account swatch is not in the DOM (or display: none)

---

### TC-EDGE-004: Rail collapse state shared with app sidebar

**Action**:
1. Visit `/home`
2. Collapse the app sidebar
3. Navigate to `/settings`

**Observation 1 — Shared state**:
1. The settings rail is rendered in the same collapsed width as the app sidebar
2. Toggling collapse on the settings rail also updates the app sidebar on next visit

---

### TC-EDGE-005: Long usernames truncate

**Preconditions**: `user.first_name = "Aaaaaaaaaaaaaaaaaaaa"`, `last_name = "Bbbbbbbbbbbbbbbbbbbb"`.

**Action**:
1. Visit `/settings`

**Observation 1 — Truncation**:
1. The account swatch and rail footer apply the `truncate` class
2. Text does not overflow the swatch container

---

### TC-EDGE-006: Unknown sub-route deep link

**Action**:
1. Visit `/settings/nope`

**Observation 1 — 404 inside layout**:
1. Next.js 404 renders inside the settings layout
2. The rail is still present
3. No overview content is rendered

---

### TC-EDGE-007: Broken nav config (regression guard)

**Preconditions**: `SETTINGS_NAV_GROUPS` mutated to drop `Members`.

**Action**:
1. Visit `/settings`

**Observation 1 — No crash, fewer rows**:
1. Only 4 rows render in the landing list
2. The rail similarly drops the item
3. No JS error

---

### TC-EDGE-008: useNavigation context missing

**Preconditions**: Harness omits `NavigationProvider`.

**Action**:
1. Visit `/settings`

**Observation 1 — Throws + boundary**:
1. `useNavigation()` throws
2. Reported in the React error boundary (⚠ unverified — confirm error boundary presence)

---

### TC-EDGE-009: Mobile pill nav loses scroll on overflow

**Preconditions**: Viewport < `lg`; many items.

**Action**:
1. Visit `/settings`
2. Inspect the pill container

**Observation 1 — Overflow scroll**:
1. Pill container has `overflow-x-auto`
2. Padding `-mx-1 px-1 pb-0.5` is applied
3. Rightmost pills reachable by swipe

---

### TC-EDGE-010: Offline navigation between rail items

**Action**:
1. Visit `/settings`
2. Disable network
3. Click a rail item

**Observation 1 — Failure graceful**:
1. Standard Next.js navigation failure surfaces
2. The rail remains
3. No zombie loading state persists

---

### TC-EDGE-011: No background data fetching on /settings

**Action**:
1. Visit `/settings` and wait 5s

**Observation 1 — No extra XHRs**:
1. After the auth-store-driven first paint, no additional XHRs originate from `/settings`

---

### TC-EDGE-012: Active mismatch — `isSidebarItemActive` regression

**Preconditions**: rail item `Overview` is `exact: true`.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Only one active**:
1. `Overview` rail item is NOT highlighted
2. Only `User settings` is highlighted

---

### TC-A11Y-001: Page has a single h1 plus per-group h2s

**Action**:
1. Visit `/settings`

**Observation 1 — Heading hierarchy**:
1. Exactly one `<h1>` is present (`Settings`)
2. Each group has its own `<h2>` heading

---

### TC-A11Y-002: Tab through overview rows

**Action**:
1. Visit `/settings`
2. Focus the first row, then press `Tab` until focus exits the overview list

**Observation 1 — Keyboard focus visible**:
1. Each row receives `focus-visible:ring-2` styling

**Observation 2 — Order matches document order**:
1. Focus visits rows in the order: User settings → Organizations → Members → Model Providers → Integrations

---

### TC-A11Y-003: Press Enter on a focused row

**Action**:
1. Visit `/settings`
2. Tab to a row
3. Press Enter

**Observation 1 — Navigation**:
1. URL becomes the row's `href`

---

### TC-A11Y-004: Rail collapse toggle reachable via keyboard

**Preconditions**: Viewport ≥ `lg`.

**Action**:
1. Visit `/settings`
2. Tab to the rail collapse handle
3. Press Space (or Enter)

**Observation 1 — Toggle fires**:
1. `sidebarCollapsed` flips in `useNavigation()`
2. The rail width updates

---

### TC-A11Y-005: Mobile pill nav arrow keys move focus without trap

**Preconditions**: Viewport < `lg`.

**Action**:
1. Visit `/settings`
2. Focus a pill
3. Press right arrow key, then left arrow key

**Observation 1 — Focus moves**:
1. Focus moves to the neighbouring pill
2. No keyboard trap (Tab still exits the nav)

---

### TC-A11Y-006: Active rail/pill items expose aria-current

**Action**:
1. Visit `/settings/members`

**Observation 1 — aria-current**:
1. The rail `Members` item has `aria-current="page"`
2. The mobile `Members` pill has `aria-current="page"`

---

### TC-A11Y-007: Tooltip on collapsed Back to app is keyboard-accessible

**Preconditions**: Viewport ≥ `lg`; rail collapsed.

**Action**:
1. Tab focus onto the collapsed `Back to app` link

**Observation 1 — Tooltip appears**:
1. The Radix `Tooltip` opens on focus with text `Back to app`

---

### TC-FULL-001: Lifecycle — overview → every sub-page → back to /home

**Preconditions**: Signed-in user.

**Action**:
1. Visit `/settings`
2. Click rail `User settings`; return to `/settings`
3. Click rail `Organizations`; return to `/settings`
4. Click rail `Members`; return to `/settings`
5. Click rail `Model Providers`; return to `/settings`
6. Click rail `Integrations`; return to `/settings`
7. Click rail `Back to app`

**Observation 1 — Sub-routes resolve**:
1. Every clicked rail item lands on the expected `/settings/*` URL

**Observation 2 — Active state updates per step**:
1. The clicked item gains `aria-current="page"` on each navigation
2. The previous active item loses it

**Observation 3 — Final landing**:
1. After clicking `Back to app`, the URL is `/home`
2. Zero Sonner toasts have appeared throughout the run
3. No XHRs originate from `/settings` itself

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above)

- [x] Empty user name → subtitle prefix dropped; initials fall back to `U` — see TC-HAPPY-002
- [x] `first_name` whitespace only — see TC-EDGE-001
- [x] `last_name` missing but `first_name` present — see TC-EDGE-002
- [x] Account swatch hidden below `sm` — see TC-EDGE-003
- [x] Rail and app sidebar share `sidebarCollapsed` state — see TC-EDGE-004
- [x] Long usernames truncate — see TC-EDGE-005
- [x] Unknown sub-route deep link → 404 inside layout — see TC-EDGE-006
- [x] Broken nav config (missing item) — see TC-EDGE-007
- [x] `useNavigation` context missing — see TC-EDGE-008
- [x] Mobile pill nav overflow scroll — see TC-EDGE-009
- [x] Offline rail navigation — see TC-EDGE-010
- [x] No background data fetching on `/settings` — see TC-EDGE-011
- [x] `isSidebarItemActive` exact-match regression — see TC-EDGE-012
- [x] Reduced motion — see TC-HAPPY-007

---

## Business Rules

- `SETTINGS_NAV_GROUPS` is the single source of truth for both the overview rows and the rail/pill items. The two surfaces never drift — changes must edit only `navConfig.ts`.
- The Overview row is intentionally only present in the rail/pill nav, not the landing page list. The landing page filters out `g.heading === null`.
- The settings rail width is shared with the main app sidebar via the `useNavigation` context.
- The page is purely presentational; no service calls happen on mount.
- Authorization gates: `/settings` requires the `tone_access_token` cookie. Per-sub-page authorization is enforced on the sub-page itself.
- The account swatch is a presentational shortcut to `/settings/profile` and is hidden on small viewports.

---

## Expected Toast Messages

The `/settings` overview page does NOT trigger any toasts itself. Toasts seen on this page must originate from the app shell or a navigation target. Tests should assert that **no** Sonner toast appears after a clean overview load (`expect(page.locator('[data-sonner-toast]')).toHaveCount(0)`).

| Trigger                                    | Toast title                          | Variant |
| ------------------------------------------ | ------------------------------------ | ------- |
| App-shell `GET /me` 401 (background)       | `Could not validate credentials`     | error   |
| Clicking a row to a sub-page               | (no toast on `/settings`)            | —       |
| Toggling rail collapse                     | (no toast)                           | —       |

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Single `<h1>` per page + per-group `<h2>`s — see TC-A11Y-001
- [x] Tab order visits every overview row — see TC-A11Y-002
- [x] Enter on a focused row navigates — see TC-A11Y-003
- [x] Rail collapse toggle keyboard-operable — see TC-A11Y-004
- [x] Mobile pill nav arrow keys move focus without trap — see TC-A11Y-005
- [x] Active rail/pill items expose `aria-current` — see TC-A11Y-006
- [x] Tooltip on collapsed `Back to app` keyboard-accessible — see TC-A11Y-007
- [ ] Color contrast: muted-foreground text on `bg-card` meets WCAG AA (⚠ unverified)

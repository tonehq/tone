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

This doc is scoped to the `/settings` landing page and the shared sidebar
shell behavior that wraps it.

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
- [ ] Subtitle `Welcome back, <FirstName>. Manage your account, workspace,
      and connected services in one place.` — the `Welcome back, …` prefix
      is omitted if `user.first_name` is empty
- [ ] Three grouped sections render in this order: `Account` → `Workspace`
      → `Configuration`
- [ ] Each group shows an uppercase heading and a sub-caption (e.g.
      `How you show up across the workspace`)

### US-2: Navigate into each sub-page

**As a** signed-in user, **I want** every row to be a single click into the
corresponding settings page, **so that** I can edit a thing with minimal
friction.

**Acceptance criteria**:

- [ ] Each row is an anchor `<Link>` with `href = item.href`
- [ ] Hovering a row updates the icon swatch to primary background and
      nudges the `ChevronRight` icon right (`group-hover:translate-x-0.5`)
- [ ] Rows render in this exact order:
  - Account → `User settings` (`/settings/profile`, `UserCircle`)
  - Workspace → `Organizations` (`/settings/organizations`, `Building2`)
  - Workspace → `Members` (`/settings/members`, `Users`)
  - Configuration → `Model Providers` (`/settings/model-providers`, `Plug`)
  - Configuration → `Integrations` (`/settings/integrations`, `Cable`)
- [ ] The ungrouped `Overview` entry in `SETTINGS_NAV_GROUPS` (heading
      `null`) is NOT shown on the overview list — filtered out by
      `SETTINGS_NAV_GROUPS.filter((g) => g.heading)`

### US-3: Use the settings sidebar rail (desktop)

**As a** signed-in user on a desktop viewport, **I want** the settings rail
to show every section plus a Back-to-app link, **so that** I can switch
sections without returning to `/settings` first.

**Acceptance criteria**:

- [ ] On viewports `lg` and up, `SidebarShell` renders on the left with the
      same items as `SETTINGS_NAV_GROUPS`
- [ ] The primary slot shows a `Back to app` link (`/home`) with an
      `ArrowLeft` in a primary-tinted swatch; collapsed view shows just the
      icon with a tooltip `Back to app`
- [ ] The footer slot shows the `AccountMenu`
- [ ] The rail shares `sidebarCollapsed` state with the app sidebar via
      `useNavigation()` so rail width stays consistent across `/home` and
      `/settings`
- [ ] Active item highlighting uses `isSidebarItemActive(pathname, item)`;
      the `Overview` item has `exact: true` so it only highlights on
      `/settings` itself, not on any `/settings/*` sub-route

### US-4: Use the mobile top-bar sections nav

**As a** mobile user, **I want** a horizontal pill nav at the top of every
settings page, **so that** I can jump between sections without a side menu.

**Acceptance criteria**:

- [ ] On viewports below `lg`, a sticky top bar shows a back arrow (→
      `/home`), the text `Settings`, and a horizontally scrollable pill nav
- [ ] Pills are rendered from `SETTINGS_NAV_ITEMS` (flat) — Overview,
      User settings, Organizations, Members, Model Providers, Integrations
- [ ] The active pill has `aria-current="page"` and uses
      `bg-sidebar-accent text-foreground`; inactive pills use
      `text-muted-foreground`

### US-5: Greet the user by name

**As a** signed-in user, **I want** my first name in the subtitle and an
avatar swatch with my initials, **so that** the page feels personalized.

**Acceptance criteria**:

- [ ] Subtitle includes `Welcome back, <first_name>. ` when first_name is
      a non-empty trimmed string; otherwise the prefix is omitted
- [ ] The top-right account swatch (desktop sm+ only) shows initials via
      `getInitials(user.first_name, user.last_name)`, falling back to `U`
- [ ] Swatch shows `<first> <last>` (joined with space) as the primary line
      or the literal `Your account` if both names are empty
- [ ] Secondary line reads `View profile`
- [ ] Swatch is a `<Link href="/settings/profile">`

### US-6: Respect reduced motion

**As a** user with reduced-motion preferences, **I want** the staggered
fade-in to be skipped, **so that** I don't see jitter on entry.

**Acceptance criteria**:

- [ ] `useReducedMotion()` returns `true` → `staggerChildren` = 0 and the
      per-row `y` offset = 0
- [ ] Default (no preference) → rows fade + translate from `y=8` to `y=0`
      with `staggerChildren: 0.04, delayChildren: 0.04, duration: 0.3`

---

## User Workflow Steps

Drives `frontend/e2e/dashboard/settings.spec.ts`.

**WF-1: Land on `/settings`** (positive)
1. User signs in via worker fixture → expected: `/home`.
2. User clicks the app sidebar `Settings` icon (or visits `/settings`) →
   expected: URL `/settings`; `SettingsOverview` renders; no API call fired
   beyond what the app sidebar/auth atom may have triggered (the overview
   page itself does NOT call any service).
3. User sees `Workspace settings` eyebrow, `Settings` h1, and a subtitle
   that includes `Welcome back, <FirstName>.` when first name is present.

**WF-2: Navigate to each sub-section** (positive)
1. User clicks `User settings` row → expected: `/settings/profile`.
2. User clicks the rail `Members` item → expected: `/settings/members`.
3. User clicks the rail `Model Providers` item → expected:
   `/settings/model-providers`.
4. User clicks the rail `Integrations` item → expected:
   `/settings/integrations`.
5. User clicks the rail `Back to app` primary slot → expected: `/home`.

**WF-3: Collapse + expand the rail** (positive)
1. User clicks the SidebarShell collapse handle → expected:
   `sidebarCollapsed` flips in `useNavigation()`; rail width shrinks;
   `Back to app` collapses to the icon-only variant with a tooltip.
2. User reloads `/settings` → expected: collapse state is persisted by the
   navigation context (`⚠ unverified` — confirm `NavigationProvider`
   persistence; default may be in-memory only).

**WF-4: Mobile pill nav** (positive)
1. User resizes the viewport below `lg` → expected: rail hides; sticky top
   bar appears with `ArrowLeft` (`/home`), `Settings` label, and pills.
2. User taps `Members` pill → expected: navigation to `/settings/members`;
   that pill gains `aria-current="page"` after page change.

**WF-5: Deep link sub-route preserves rail** (positive)
1. User opens a fresh tab and pastes `/settings/members` → expected: rail
   renders with `Members` active (no flash of `Overview` active); the
   overview landing card list does NOT render.

**WF-6: Active-state Overview only on `/settings`** (positive)
1. User on `/settings` → expected: `Overview` rail item is active.
2. User on `/settings/profile` → expected: `Overview` is NOT active (it has
   `exact: true`); only `User settings` is highlighted.

**WF-7: Unauthenticated access** (negative)
1. User clears the `tone_access_token` cookie and visits `/settings` →
   expected: middleware redirect to
   `/auth/login?redirect=%2Fsettings`.

---

## Input Specifications

The overview page has **no input fields**. The only interactive elements
are anchor links and the rail collapse toggle (handled by `SidebarShell`).

| Control                | Type     | Validation | Behavior                                |
| ---------------------- | -------- | ---------- | --------------------------------------- |
| Row link (overview)    | `<a>`    | n/a        | Navigate to `item.href`                 |
| Rail item              | `<a>`    | n/a        | Navigate; active state per pathname     |
| Back-to-app (rail)     | `<a>`    | n/a        | Navigate to `/home`                     |
| Account swatch (desk.) | `<a>`    | n/a        | Navigate to `/settings/profile`         |
| Mobile back arrow      | `<a>`    | n/a        | Navigate to `/home`                     |
| Mobile pill            | `<a>`    | n/a        | Navigate; `aria-current` reflects state |
| Collapse handle        | button   | n/a        | `useNavigation().toggleSidebar()`       |

---

## Success Scenarios

**PS-1: Overview renders for a known user**
- Preconditions: signed-in; `user.first_name = "Jane"`, `last_name = "Doe"`.
- Steps: navigate to `/settings`.
- Expected: subtitle starts `Welcome back, Jane.`; account swatch shows
  initials `JD` and primary line `Jane Doe`; three group sections render.
- **Mock API**: none required for this page; `useAuthStore` is hydrated from
  the `login_data` cookie. For test setup, seed the cookie before navigation.

**PS-2: Overview renders for an unnamed user**
- Preconditions: signed-in; `user.first_name = ""`, `last_name = ""`.
- Steps: navigate to `/settings`.
- Expected: subtitle has NO `Welcome back, …` prefix and starts
  `Manage your account, …`; account swatch shows initials `U` and primary
  line `Your account`.

**PS-3: Each overview row navigates correctly**
- Preconditions: PS-1.
- Steps: click each of the 5 rows.
- Expected: URLs in order `/settings/profile`, `/settings/organizations`,
  `/settings/members`, `/settings/model-providers`, `/settings/integrations`.

**PS-4: Desktop rail renders Back-to-app + 6 items**
- Preconditions: PS-1; viewport ≥ `lg`.
- Steps: assert rail.
- Expected: primary slot `Back to app` link visible (text `Settings` +
  `Back to app`); 6 nav items rendered (`Overview`, `User settings`,
  `Organizations`, `Members`, `Model Providers`, `Integrations`); footer
  shows `AccountMenu`.

**PS-5: Mobile pill nav**
- Preconditions: PS-1; viewport < `lg`.
- Steps: assert the top bar.
- Expected: back arrow `<a aria-label="Back to app">`, label `Settings`,
  pill nav with 6 items, current page pill has `aria-current="page"`.

**PS-6: Active rail item updates on navigation**
- Preconditions: PS-4.
- Steps: click rail `Members`.
- Expected: URL `/settings/members`; rail `Members` item gets active styling
  (test via `[aria-current="page"]` or asserted active class); `Overview`
  loses active styling.

**PS-7: Reduced motion**
- Preconditions: emulate `prefers-reduced-motion: reduce`.
- Steps: navigate to `/settings`.
- Expected: rows are present without the staggered fade-in transform; no
  hidden initial frame visible to the user.

---

## Failure Scenarios

**FS-1: No auth cookie**
- Preconditions: unauthenticated.
- Steps: navigate to `/settings`.
- **Mock API**: n/a (middleware-level).
- Expected UI: browser redirects to `/auth/login?redirect=%2Fsettings`; no
  `SettingsOverview` markup rendered.

**FS-2: Stale token (401 on background refresh)**
- Preconditions: cookie present but expired.
- **Mock API**: any background `GET /me`-style call →
  `401 { "detail": "Could not validate credentials" }` (`⚠ unverified` —
  overview itself does not call APIs; rejection comes from app shell or
  `AccountMenu`).
- Expected UI: overview still renders the static markup (user fields may be
  missing → subtitle has no `Welcome back, …` prefix, initials fall back to
  `U`). No toast triggered by `/settings` directly.

**FS-3: `useAuthStore` returns `undefined`**
- Preconditions: cookie present but `login_data` failed to parse.
- Expected UI: subtitle omits `Welcome back, …`; account swatch initials =
  `U`; rest of overview renders normally.

**FS-4: Broken nav config (missing item)**
- Preconditions: `SETTINGS_NAV_GROUPS` is mutated to drop `Members`
  (regression test).
- Expected UI: only 4 rows render; rail similarly drops the item; no crash.
  Treat as a unit-level guard.

**FS-5: Unknown sub-route deep link**
- Preconditions: signed-in.
- Steps: navigate to `/settings/nope`.
- Expected UI: Next.js 404 renders inside the settings layout (rail still
  present); no overview content renders.

**FS-6: Rail link to a 5xx page**
- Preconditions: signed-in; user clicks rail `Members`; the members API
  returns `500`.
- Expected UI: navigation to `/settings/members` succeeds; the failure
  surfaces on that page (not `/settings`); the rail's active state still
  reflects `Members`.

**FS-7: useNavigation context missing**
- Preconditions: harness omits `NavigationProvider` (test regression).
- Expected UI: `useNavigation()` throws; layout crashes; reported in the
  React error boundary above (`⚠ unverified` — confirm error boundary
  presence). Add a regression unit test for the provider.

**FS-8: Hover on row without pointer support**
- Preconditions: keyboard-only navigation.
- Steps: Tab through overview rows.
- Expected UI: each row exposes `focus-visible:ring-2` styling; Enter
  navigates; no broken focus trap.

**FS-9: Active mismatch — `isSidebarItemActive` regression**
- Preconditions: signed-in; rail item `Overview` is `exact: true`.
- Steps: navigate to `/settings/profile`.
- Expected UI: `Overview` rail item NOT highlighted; only `User settings`
  highlighted. If both highlight, regression — fix `exact` handling in
  `SidebarShell.isSidebarItemActive`.

**FS-10: Mobile pill nav loses scroll on overflow**
- Preconditions: viewport < `lg`; many items.
- Expected UI: pill container has `overflow-x-auto` and `-mx-1 px-1
  pb-0.5` padding; rightmost pills reachable by swiping.

---

## Expected Toast Messages

The `/settings` overview page does NOT trigger any toasts itself. Toasts
seen on this page must originate from the app shell (e.g. session expiry)
or from a navigation target. For completeness:

| Trigger                                    | Toast title                          | Variant |
| ------------------------------------------ | ------------------------------------ | ------- |
| App-shell `GET /me` 401 (background)       | `Could not validate credentials`     | error   |
| Clicking a row to a sub-page               | (no toast on `/settings`; sub-page may emit one) | — |
| Toggling rail collapse                     | (no toast)                           | —       |

Tests for this page should assert that **no** Sonner toast appears after a
clean overview load (`expect(page.locator('[data-sonner-toast]')).toHaveCount(0)`).

---

## UI Elements

| Element                  | Type           | Content / Label                                                       | Behavior                                          |
| ------------------------ | -------------- | --------------------------------------------------------------------- | ------------------------------------------------- |
| Eyebrow                  | text           | `Workspace settings`                                                  | Static; primary-color dot + uppercase tracking    |
| Page heading             | h1             | `Settings`                                                            | Static                                            |
| Subtitle                 | p              | `Welcome back, <Name>. Manage your account, workspace, and connected services in one place.` | Greeting prefix conditional on `user.first_name` |
| Account swatch (desktop) | `<Link>`       | initials + name + `View profile`                                      | Visible `sm:` and up; navigates to `/settings/profile` |
| Group section heading    | h2             | `ACCOUNT` / `WORKSPACE` / `CONFIGURATION` (uppercase tracking)         | Static                                            |
| Group caption            | p              | Per-group caption from `navConfig`                                    | Static                                            |
| Overview row             | `<Link>`       | icon swatch + label + description + `ChevronRight`                    | Hover lifts icon swatch to primary; chevron slides |
| Row — User settings      | `<Link>`       | `UserCircle` icon, `Manage your profile, avatar, and personal account details.` | Navigates to `/settings/profile`         |
| Row — Organizations      | `<Link>`       | `Building2` icon, `Create and switch between the workspaces you belong to.` | Navigates to `/settings/organizations`      |
| Row — Members            | `<Link>`       | `Users` icon, `Invite teammates and manage their roles and access.`   | Navigates to `/settings/members`                  |
| Row — Model Providers    | `<Link>`       | `Plug` icon, `Configure LLM, speech-to-text, and text-to-speech provider keys.` | Navigates to `/settings/model-providers` |
| Row — Integrations       | `<Link>`       | `Cable` icon, `Connect external apps and manage API credentials.`     | Navigates to `/settings/integrations`             |
| Rail primary (desktop)   | `<Link>`       | `Settings` + `Back to app` (or icon-only when collapsed)              | Navigates to `/home`                              |
| Rail item                | `<Link>`       | icon + label                                                          | `aria-current="page"` when active                 |
| Rail footer              | component      | `AccountMenu`                                                         | Account menu actions                              |
| Mobile back arrow        | `<Link>`       | `ArrowLeft` icon, `aria-label="Back to app"`                          | Navigates to `/home`                              |
| Mobile header label      | span           | `Settings`                                                            | Static                                            |
| Mobile pill              | `<Link>`       | icon + label                                                          | `aria-current="page"` when active                 |

---

## Navigation

| Trigger                          | Destination                              | Condition                              |
| -------------------------------- | ---------------------------------------- | -------------------------------------- |
| Visit `/settings` (auth'd)       | Renders `SettingsOverview`               | `tone_access_token` cookie present     |
| Visit `/settings` (no auth)      | `/auth/login?redirect=%2Fsettings`       | Middleware match for `(dashboard)`     |
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

The `/settings` landing page itself makes **no API calls**. It reads the
user object from the Zustand `useAuthStore` (which is hydrated from cookies
set during login).

Sub-pages do call APIs; those contracts belong in their own feature docs:

| Sub-route                  | Owning doc            |
| -------------------------- | --------------------- |
| `/settings/profile`        | `user-settings.md`    |
| `/settings/organizations`  | `organizations.md`    |
| `/settings/members`        | `members.md`          |
| `/settings/model-providers`| `model-providers.md` + `model-providers-detail.md` |
| `/settings/integrations`   | `oauth-integrations.md` + `channels.md` + `mcp-servers.md` + `knowledge-base.md` |

If a test harness needs an auth-store seed without a live API, set the
`tone_access_token`, `org_tenant_id`, and `login_data` cookies before
navigation. The `login_data` cookie shape (from `AuthAtom.tsx`):

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

> `⚠ unverified` — confirm exact cookie name + JSON shape in
> `src/atoms/AuthAtom.tsx` / `src/stores/auth.ts`. Most existing E2E specs
> use the `MOCK_JWT` constant from `test-patterns.md`.

---

## Edge Cases

- [ ] Empty user name → subtitle prefix dropped; initials fall back to `U`;
      account swatch primary line reads `Your account`
- [ ] `first_name` is whitespace only → `firstName.trim()` short-circuits;
      treated as empty for greeting
- [ ] `last_name` missing but `first_name` present → initials use just the
      first letter of `first_name` (`getInitials` truncates safely)
- [ ] Reduced-motion preference set → no `y` offset or stagger
- [ ] Account swatch hidden below `sm` (always hidden on small viewports)
- [ ] Desktop rail and app sidebar share `sidebarCollapsed` state; the
      collapsed/expanded width is identical across `/home` and `/settings`
- [ ] Active state for `Overview` rail item is `exact: true` — does NOT
      light up on any sub-route
- [ ] Mobile pill nav uses horizontal scroll (`overflow-x-auto`) when items
      exceed viewport width
- [ ] Long usernames truncate via `truncate` class — both in the account
      swatch and in the rail footer's `AccountMenu`
- [ ] Hover on a row uses `group-hover` to update icon swatch background,
      ring, foreground color, and chevron transform together
- [ ] `focus-visible:ring-2 ring-inset ring-ring` styling on rows makes
      keyboard nav clearly visible
- [ ] The settings layout does NOT show the main app sidebar — only the
      settings rail (and only on desktop)
- [ ] `useNavigation()` exposes `sidebarCollapsed` + `toggleSidebar`; if
      the provider is missing the layout will throw at render time
- [ ] No background data fetching occurs on `/settings` — assert no
      additional XHRs after the auth-store-driven first paint
- [ ] No analytics event fires on row click from this page (verify in
      tests; subpages may instrument their own)

---

## Business Rules

- `SETTINGS_NAV_GROUPS` is the single source of truth for both the
  overview rows and the rail/pill items. The two surfaces never drift —
  changes must edit only `navConfig.ts`.
- The Overview row is intentionally only present in the rail/pill nav, not
  the landing page list. The landing page filters out
  `g.heading === null`.
- The settings rail width is shared with the main app sidebar via the
  `useNavigation` context so toggling collapse on one persists on the other.
- The page is purely presentational; no service calls happen on mount.
- Authorization gates: `/settings` requires the `tone_access_token` cookie.
  Per-sub-page authorization (org-owner only for Members invites, etc.) is
  enforced on the sub-page itself.
- The account swatch is a presentational shortcut to `/settings/profile`
  and is hidden on small viewports to avoid duplicating the mobile pill nav.

---

## Accessibility Requirements

- [ ] Page has a single `<h1>` (`Settings`)
- [ ] Each group has an `<h2>` heading
- [ ] Each overview row is a single focusable link with a clear accessible
      name (label) and a description (announced via the link text content)
- [ ] Rail `Back to app` link has either visible label `Settings` /
      `Back to app` (expanded) or `aria-label="Back to app"` (collapsed)
- [ ] Mobile back-to-app arrow uses `aria-label="Back to app"`
- [ ] Active rail/pill item uses `aria-current="page"`
- [ ] Row, rail, and pill links all expose `focus-visible:ring-2` (or
      equivalent) for keyboard users
- [ ] `useReducedMotion()` is honored — no involuntary motion for users
      with motion-reduction preferences
- [ ] Color contrast: muted-foreground text (`text-muted-foreground`) on
      `bg-card` must meet WCAG AA (`⚠ unverified` — confirm against theme
      tokens in `globals.css`)
- [ ] Icon swatch backgrounds are decorative; the row label provides the
      semantic name
- [ ] Tooltip on the collapsed `Back to app` link is keyboard-accessible
      (Radix `Tooltip` opens on focus)
- [ ] Mobile pill nav scrolls horizontally with arrow keys / swipe; no
      keyboard trap (`⚠ unverified` — verify `SidebarShell` behavior)

---

## E2E Scenarios — gap-filling

> Scenarios IDs use the `SET-` prefix for the `/settings` landing page.
> Existing FS-/PS-/WF- entries above remain unchanged; the table below is the
> append-only gap-fill that `/generate-tests` reads.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-001 | Visit `/settings` without auth cookie | Middleware redirects to `/auth/login?redirect=%2Fsettings` | `unauthenticated visit redirects to login` |
| SET-002 | Visit `/settings` with an expired `tone_access_token` | Same redirect; expired cookie is cleared by middleware (or on next /me 401) | `expired token redirects to login and clears cookie` |
| SET-003 | Visit `/settings/profile` deep link without auth | Redirect to `/auth/login?redirect=%2Fsettings%2Fprofile` (rail not rendered) | `deep link sub-route without auth redirects with correct redirect param` |
| SET-004 | Member (non-owner) visits `/settings` | Page still renders (no role gate on the overview itself) | `member can access the settings overview` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-010 | Background `GET /user/me` returns 401 mid-session | Overview still renders with fallback user (initials `U`, no `Welcome back`); no client-side crash | `401 background refresh degrades gracefully` |
| SET-011 | Background `GET /user/me` returns 500 | Overview renders with cached user from `login_data` cookie; no toast on this page | `500 background refresh degrades gracefully` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-020 | Slow `GET /user/me` (>3s) during initial paint | Overview renders eagerly from cookie; later hydrate updates greeting without flicker | `slow /me hydrates greeting without flicker` |
| SET-021 | Offline navigation between rail items | Standard Next.js failure; rail remains; no zombie loading state | `offline rail navigation surfaces failure gracefully` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-030 | Tab through overview rows | Each row receives `focus-visible:ring-2`; Enter activates link | `keyboard tab order visits every overview row in document order` |
| SET-031 | Press Enter on a focused row | Navigates to the row's href | `Enter on focused row navigates to the sub-page` |
| SET-032 | Rail collapse toggle reachable via keyboard | Space/Enter on collapse handle toggles `sidebarCollapsed` | `collapse handle is keyboard-operable` |
| SET-033 | Mobile pill nav uses left/right arrow keys to scroll | Arrow keys move focus to neighbouring pill without trapping | `mobile pill nav arrow keys move focus without trap` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-040 | Click rail `Back to app` | Navigates to `/home`; main app sidebar reappears | `Back to app returns to /home` |
| SET-041 | Browser Back after navigating to `/settings/profile` | Returns to `/settings` overview with `Overview` rail item active | `browser back from sub-route returns to overview` |
| SET-042 | Click account swatch on desktop | Navigates to `/settings/profile` (single hop, no flash of overview) | `desktop account swatch navigates to /settings/profile` |
| SET-043 | Mobile back arrow | Navigates to `/home` (viewport < lg) | `mobile back arrow returns to /home` |

### Full lifecycle test

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| SET-FULL | Land on `/settings` → click each rail item in order → return via `Back to app` | Every sub-route resolves, active state updates, final URL is `/home`; no toasts; no XHRs from `/settings` itself | `lifecycle: overview → every sub-page → back to /home` |

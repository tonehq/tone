# Feature Doc: Home Page

Feature documentation for the dashboard home page. Used by `/generate-tests home`
to ensure all user cases are covered alongside the component source analysis.

---

## Page

- **Route**: `/home`
- **Component**: `src/app/(dashboard)/home/page.tsx`
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fhome` without `tone_access_token` cookie)

---

## User Stories

### US-1: View dashboard overview

**As a** logged-in user, **I want to** see a welcome message and key stats on the home page, **so that** I get a quick overview of my account.

**Acceptance criteria**:

- [x] Shows "Welcome to Tone" heading (h4)
- [x] Shows subtitle: "Build and deploy AI voice agents in minutes..."
- [x] Displays 4 stats cards: Total Agents, Active Calls, Minutes Used, Success Rate
- [x] Each stats card shows label, value (h4), and change/period text

### US-2: Navigate to features via quick links

**As a** logged-in user, **I want to** click quick link cards to navigate to feature pages, **so that** I can quickly access the tools I need.

**Acceptance criteria**:

- [x] Shows 6 quick link cards: Agents, Phone Numbers, Analytics, Actions, Team Members, Settings
- [x] Each card shows icon, title (h6), and description
- [x] Clicking a card navigates to the correct route
- [x] Cards are rendered as `<a>` tags (accessible links)
- [x] Keyboard navigation works (Tab between cards, Enter to activate)

### US-3: Auth protection

**As the** system, **I want to** redirect unauthenticated users to the login page, **so that** only logged-in users can access the dashboard.

**Acceptance criteria**:

- [x] Redirects to `/auth/login?redirect=%2Fhome` when no `tone_access_token` cookie
- [x] Stays on `/home` when valid auth cookies are present
- [x] After login, 4 cookies are set: `tone_access_token`, `org_tenant_id`, `login_data`, `user_id`

---

## UI Elements

| Element             | Type        | Content / Label                       | Behavior                      |
| ------------------- | ----------- | ------------------------------------- | ----------------------------- |
| Welcome heading     | h4          | "Welcome to Tone"                     | Static text                   |
| Subtitle            | body1       | "Build and deploy AI voice agents..." | Static text                   |
| Total Agents card   | Card        | label + "6" + "+2 this week"          | Non-interactive               |
| Active Calls card   | Card        | label + "0" + "Real-time"             | Non-interactive               |
| Minutes Used card   | Card        | label + "0" + "This month"            | Non-interactive               |
| Success Rate card   | Card        | label + "0%" + "Last 30 days"         | Non-interactive               |
| Quick Links heading | h6          | "Quick Links"                         | Static text                   |
| Agents card         | Card (link) | icon + "Agents" + description         | Navigates to `/agents`        |
| Phone Numbers card  | Card (link) | icon + "Phone Numbers" + description  | Navigates to `/phone-numbers` |
| Analytics card      | Card (link) | icon + "Analytics" + description      | Navigates to `/analytics`     |
| Actions card        | Card (link) | icon + "Actions" + description        | Navigates to `/actions`       |
| Team Members card   | Card (link) | icon + "Team Members" + description   | Navigates to `/settings`      |
| Settings card       | Card (link) | icon + "Settings" + description       | Navigates to `/settings`      |

---

## Navigation

| Trigger                   | Destination                    | Condition           |
| ------------------------- | ------------------------------ | ------------------- |
| Click Agents card         | `/agents`                      | Always              |
| Click Phone Numbers card  | `/phone-numbers`               | Always              |
| Click Analytics card      | `/analytics`                   | Always              |
| Click Actions card        | `/actions`                     | Always              |
| Click Team Members card   | `/settings`                    | Always              |
| Click Settings card       | `/settings`                    | Always              |
| Enter key on focused card | Card's href                    | Always              |
| No auth cookie            | `/auth/login?redirect=%2Fhome` | Middleware redirect |

---

## API Contracts

None — this is a static page with hardcoded data. No API calls.

---

## Edge Cases

- [x] Unauthenticated access → redirect to login
- [x] Redirect preserves the `?redirect=%2Fhome` query param
- [x] Stats cards are non-interactive (no link role, no click handler)
- [x] Sidebar and main content coexist (dashboard layout)
- [x] Two cards share the same href (`/settings`) — Team Members and Settings

---

## Business Rules

- Stats values are currently hardcoded (not fetched from API)
- Quick link cards use `next/link` for client-side navigation
- The page is a `'use client'` component (uses `useTheme()`)

---

## Accessibility Requirements

- [x] Heading hierarchy: h4 (Welcome) → h6 (Quick Links, card titles)
- [x] Quick link cards rendered as `<a>` elements (semantic links)
- [x] Tab navigation through quick link cards in DOM order
- [x] Enter key activates focused quick link card
- [x] Stats cards have no link role (correctly non-interactive)
- [x] Card titles disambiguated from sidebar links by full accessible name

---

## Appended Scenarios (gap-fill, ID prefix `HM-`)

These rows extend the original US/UI coverage with auth/error-state/network/a11y/dashboard-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `home.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-001 | Visit `/home` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fhome` | `unauthenticated visit redirects to login` |
| HM-002 | Visit `/home` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Fhome`; expired cookie cleared on the login response | `expired token redirects to login and clears cookie` |
| HM-003 | Visit `/` (root) when authenticated | Server-side redirect lands on `/home` and renders the welcome heading | `root path redirects to home for authenticated user` |
| HM-004 | Logout from sidebar then revisit `/home` | Middleware redirect back to `/auth/login?redirect=%2Fhome`; `tone_access_token` cookie cleared | `logout clears cookies and blocks return to home` |

### Backend error states (sidebar / shell shared by home)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-005 | Token expires mid-session, user clicks a quick-link card | Card navigation completes; the next protected fetch fails 401 and the target page surfaces the standard error toast | `quick-link navigation after token expiry triggers downstream 401 handling` |
| HM-006 | Sidebar org switcher fetch returns 500 | Home page still renders cards; only the org chip surfaces an error state; no client crash | `home renders even when shell-level fetches fail` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-007 | Offline / network failure during the initial load | Welcome heading + cards still paint (page is hardcoded); no infinite spinner; no toast spam | `offline load still renders the static dashboard` |
| HM-008 | Slow shell hydration (>3s) | Welcome heading + cards visible immediately; sidebar may render skeleton until ready; no blocking overlay | `slow shell hydration does not block home content` |

### Input edge cases (quick-link card interactions)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-009 | Click each quick-link card in turn | Each click navigates to its href; back-button returns to `/home` with cards intact | `each quick link card navigates to the documented route` |
| HM-010 | Rapid double-click on a quick-link card | Only one navigation occurs; no duplicate router push entries | `rapid double-click does not duplicate navigation` |
| HM-011 | Open quick-link card in a new tab via Cmd/Ctrl-click | Original tab stays on `/home`; new tab opens the target route | `cmd-click opens quick link in a new tab` |

### Dashboard-specific

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-012 | Stats cards render labels + values + change/period text | All four stats cards render their full content; values are stable (hardcoded today) | `stats cards display label value and period text` |
| HM-013 | Stats cards are non-interactive | No click handler, no link role; clicking the card body does not navigate | `stats cards do not navigate on click` |
| HM-014 | Empty state for a new org (no calls yet) | Active Calls / Minutes Used / Success Rate show `0` / `0` / `0%`; subtitles encourage first-call setup | `new org sees zeroed stats with onboarding subtitles` |
| HM-015 | Welcome heading hierarchy | Exactly one h4 "Welcome to Tone"; one h6 "Quick Links"; six h6 card titles | `welcome heading hierarchy matches the documented levels` |
| HM-016 | Cross-feature navigation — Team Members card and Settings card share `/settings` | Both routes resolve, both cards land on the same destination | `team members and settings cards both navigate to settings` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-017 | Tab through quick-link cards in DOM order | Focus visits Agents → Phone Numbers → Analytics → Actions → Team Members → Settings | `tab order through quick link cards matches DOM order` |
| HM-018 | Press Enter on a focused quick-link card | Navigates to the card's href just like a click | `Enter on focused quick link card activates navigation` |
| HM-019 | Press Space on a focused quick-link card (anchor element) | No navigation (Space does not activate `<a>`); accessible name still announced | `Space on quick link card does not navigate` |
| HM-020 | Stats cards skipped in tab order | Pressing Tab from the welcome region jumps past stats cards directly to the first quick-link card | `stats cards are not focusable in tab order` |
| HM-021 | Screen reader landmark structure | Page exposes `<main>` landmark; sidebar exposes `<nav>` landmark; both are uniquely labeled | `home exposes main and nav landmarks for screen readers` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-022 | Back button after clicking Agents card | Returns to `/home`; cards visible without re-flicker | `back button after agents card click returns to home` |
| HM-023 | Forward button after back | Forward returns to `/agents` | `forward navigation returns to last visited card route` |
| HM-024 | Hard reload on `/home` after navigation | Reload renders the dashboard; no auth redirect for an authenticated user | `hard reload preserves home page for authenticated user` |

### Full lifecycle (`HM-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| HM-FULL | Authenticate via `loginViaUI` → land on `/home` → assert welcome heading + subtitle + 4 stats cards + Quick Links heading + 6 card titles → Tab through all 6 quick-link cards verifying focus order → Enter on the Agents card → assert URL is `/agents` → browser back → assert URL is `/home` and cards intact → click Phone Numbers card → assert URL is `/phone-numbers` → back → click Settings card → assert URL is `/settings` → log out from sidebar → assert redirect to `/auth/login` and revisiting `/home` redirects with `?redirect=%2Fhome` | Every documented affordance fires the expected navigation; no leaked listeners; no test data to clean (page is hardcoded) | `walks the entire home dashboard end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| HM-001..004 | US-3 (auth gating) | Adds expired-token + logout cases on top of the bare unauth redirect |
| HM-005..006 | (new) | Backend error scenarios on the shared dashboard shell |
| HM-007..008 | (new) | Network resilience for a static-data page |
| HM-009..011 | US-2 acceptance criteria | Adds rapid-click + cmd-click edge cases |
| HM-012..016 | US-1 acceptance criteria | Promotes stats/cards/empty-state checks to runnable scenarios |
| HM-017..021 | Accessibility section | Promotes a11y bullets to scenarios |
| HM-022..024 | Navigation table | Adds browser back/forward + reload checks |
| HM-FULL | (new) | Single-test sweep of the home dashboard |

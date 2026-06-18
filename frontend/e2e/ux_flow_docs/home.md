# Feature Doc: Home Page

Feature documentation for the dashboard home page. Used by `/generate-tests home`
to ensure all user cases are covered alongside the component source analysis.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-ERROR-` (server errors), `TC-NAV-` (navigation),
> `TC-LOADING-` (loading/disabled), `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility),
> `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Welcome heading + stats cards render for authenticated user

**Preconditions**:
- User has all 4 auth cookies (`tone_access_token`, `org_tenant_id`, `login_data`, `user_id`)

**Action**:
1. Visit `/home`

**Observation 1 — Welcome region renders**:
1. h4 heading text equals `Welcome to Tone`
2. Subtitle paragraph contains `Build and deploy AI voice agents`

**Observation 2 — Four stats cards render**:
1. A card with label `Total Agents`, value `6`, and change text `+2 this week` is visible
2. A card with label `Active Calls`, value `0`, and period text `Real-time` is visible
3. A card with label `Minutes Used`, value `0`, and period text `This month` is visible
4. A card with label `Success Rate`, value `0%`, and period text `Last 30 days` is visible

**Observation 3 — Quick Links region renders**:
1. h6 heading text equals `Quick Links`
2. Six quick link cards are visible (Agents, Phone Numbers, Analytics, Actions, Team Members, Settings)

---

### TC-HAPPY-002: Each quick link card navigates to documented route

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Click the Agents card
2. Press browser Back
3. Click the Phone Numbers card
4. Press browser Back
5. Repeat for Analytics, Actions, Team Members, Settings

**Observation 1 — Agents card navigates**:
1. After clicking Agents card, URL becomes `/agents`

**Observation 2 — Phone Numbers card navigates**:
1. After clicking Phone Numbers card, URL becomes `/phone-numbers`

**Observation 3 — Analytics card navigates**:
1. After clicking Analytics card, URL becomes `/analytics`

**Observation 4 — Actions card navigates**:
1. After clicking Actions card, URL becomes `/actions`

**Observation 5 — Team Members + Settings both go to /settings**:
1. Team Members card navigates to `/settings`
2. Settings card navigates to `/settings`

---

### TC-NAV-001: Unauthenticated visit redirects to login (HM-001)

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/home`

**Observation 1 — Middleware redirect**:
1. Response status is 307
2. Final URL becomes `/auth/login?redirect=%2Fhome`

---

### TC-NAV-002: Expired token redirects to login and clears cookie (HM-002)

**Preconditions**: Browser has an expired `tone_access_token` cookie.

**Action**:
1. Visit `/home`

**Observation 1 — Middleware redirect**:
1. Response status is 307
2. Final URL becomes `/auth/login?redirect=%2Fhome`

**Observation 2 — Expired cookie cleared**:
1. The expired `tone_access_token` cookie is cleared on the login response

---

### TC-NAV-003: Root path redirects to home for authenticated user (HM-003)

**Preconditions**: User has all 4 auth cookies.

**Action**:
1. Visit `/` (root)

**Observation 1 — Server-side redirect**:
1. Final URL becomes `/home`
2. The Welcome heading is visible

---

### TC-NAV-004: Logout clears cookies and blocks return to /home (HM-004)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Click Logout from the sidebar
2. Revisit `/home`

**Observation 1 — Cookies cleared**:
1. `tone_access_token` cookie is no longer set

**Observation 2 — Middleware redirect on revisit**:
1. Visiting `/home` again redirects to `/auth/login?redirect=%2Fhome`

---

### TC-NAV-005: Back button after Agents card click returns to home (HM-022)

**Preconditions**: Authenticated user on `/home`; just clicked the Agents card and landed on `/agents`.

**Action**:
1. Press browser Back

**Observation 1 — Returns to /home**:
1. URL becomes `/home`
2. Stats cards and Quick Links cards remain visible without flicker

---

### TC-NAV-006: Forward button after back returns to last route (HM-023)

**Preconditions**: Following TC-NAV-005, user is back on `/home` after visiting `/agents`.

**Action**:
1. Press browser Forward

**Observation 1 — Forward navigates to /agents**:
1. URL becomes `/agents`

---

### TC-NAV-007: Hard reload preserves /home for authenticated user (HM-024)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Perform a hard reload of the page

**Observation 1 — Page re-renders without auth redirect**:
1. URL stays at `/home`
2. Welcome heading visible again
3. No redirect to `/auth/login` occurs

---

### TC-ERROR-001: Quick-link navigation after token expiry triggers downstream 401 (HM-005)

**Preconditions**: Authenticated user on `/home`; token expires after page load.

**Action**:
1. Click a quick-link card (e.g. Agents)

**Observation 1 — Navigation completes**:
1. URL becomes the card's href (`/agents`)

**Observation 2 — Downstream 401 surfaces toast**:
1. The next protected fetch on the target page fails with 401
2. The target page surfaces the standard error toast

---

### TC-ERROR-002: Home renders even when shell-level fetches fail (HM-006)

**Preconditions**: Authenticated user; sidebar org switcher API returns 500.

**Action**:
1. Visit `/home`

**Observation 1 — Home page still renders**:
1. Welcome heading is visible
2. All 4 stats cards are visible
3. All 6 quick-link cards are visible
4. No client crash occurs

**Observation 2 — Sidebar surfaces its own error**:
1. Only the org chip in the sidebar surfaces an error state

---

### TC-LOADING-001: Offline load still renders the static dashboard (HM-007)

**Preconditions**: Authenticated user; network is offline.

**Action**:
1. Visit `/home`

**Observation 1 — Static content paints**:
1. Welcome heading is visible
2. All 6 quick-link cards are visible
3. No infinite spinner is shown
4. No toast spam occurs

---

### TC-LOADING-002: Slow shell hydration does not block home content (HM-008)

**Preconditions**: Authenticated user; shell hydration delayed by >3 s.

**Action**:
1. Visit `/home`

**Observation 1 — Home content paints immediately**:
1. Welcome heading visible without waiting for the shell
2. Quick-link cards visible immediately

**Observation 2 — Sidebar may render skeleton**:
1. Sidebar may show a skeleton state until shell is ready
2. No blocking overlay covers the main content

---

### TC-EDGE-001: Rapid double-click on a quick-link card (HM-010)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Double-click the Agents card rapidly (≤ 100 ms apart)

**Observation 1 — Single navigation only**:
1. URL becomes `/agents` exactly once
2. Router history contains only one new entry (no duplicates)

---

### TC-EDGE-002: Cmd/Ctrl-click opens quick link in a new tab (HM-011)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Cmd-click (macOS) or Ctrl-click (Windows/Linux) the Phone Numbers card

**Observation 1 — Original tab stays on /home**:
1. The current tab URL is still `/home`

**Observation 2 — New tab opens target**:
1. A new browser tab opens at `/phone-numbers`

---

### TC-EDGE-003: Stats cards do not navigate on click (HM-013)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Click the body of the Total Agents stats card
2. Click the body of the Active Calls stats card
3. Click the body of the Minutes Used stats card
4. Click the body of the Success Rate stats card

**Observation 1 — No navigation occurs**:
1. URL stays at `/home`
2. No router push events fire

**Observation 2 — No interactive role**:
1. Stats cards have no `role="link"` or `role="button"`
2. Stats cards have no `onClick` handler

---

### TC-EDGE-004: New org sees zeroed stats with onboarding subtitles (HM-014)

**Preconditions**: Authenticated user for a new org (no calls yet).

**Action**:
1. Visit `/home`

**Observation 1 — Active Calls / Minutes Used / Success Rate are zeroed**:
1. Active Calls card shows `0`
2. Minutes Used card shows `0`
3. Success Rate card shows `0%`

**Observation 2 — Subtitles encourage first-call setup**:
1. Card subtitles describe the empty state (e.g. `Real-time`, `This month`, `Last 30 days`)

---

### TC-EDGE-005: Welcome heading hierarchy matches documented levels (HM-015)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Visit `/home`
2. Inspect the heading hierarchy

**Observation 1 — Heading counts match**:
1. Exactly one h4 with text `Welcome to Tone` exists
2. Exactly one h6 with text `Quick Links` exists
3. Exactly six h6 elements exist for the quick-link card titles

---

### TC-A11Y-001: Tab order through quick-link cards matches DOM order (HM-017)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Focus the welcome region
2. Press Tab repeatedly until focus moves past all quick links

**Observation 1 — Tab visits cards in DOM order**:
1. Focus order is: Agents → Phone Numbers → Analytics → Actions → Team Members → Settings
2. No card is skipped
3. No card is reached twice

---

### TC-A11Y-002: Enter on focused quick-link card activates navigation (HM-018)

**Preconditions**: Authenticated user on `/home`; Agents card is focused.

**Action**:
1. Press the Enter key

**Observation 1 — Navigation fires**:
1. URL becomes `/agents`

---

### TC-A11Y-003: Space on focused quick-link card does not navigate (HM-019)

**Preconditions**: Authenticated user on `/home`; Agents card (`<a>`) is focused.

**Action**:
1. Press the Space key

**Observation 1 — No navigation**:
1. URL stays `/home` (Space does not activate `<a>` elements)

**Observation 2 — Accessible name announced**:
1. The card's accessible name (e.g. `Agents`) is still exposed to screen readers

---

### TC-A11Y-004: Stats cards skipped in tab order (HM-020)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Focus the welcome region
2. Press Tab

**Observation 1 — Focus skips stats cards**:
1. Focus jumps directly from the welcome region to the first quick-link card
2. None of the four stats cards receive focus

---

### TC-A11Y-005: Home exposes main and nav landmarks (HM-021)

**Preconditions**: Authenticated user on `/home`.

**Action**:
1. Visit `/home`
2. Inspect ARIA landmarks

**Observation 1 — Main landmark**:
1. A `<main>` landmark is present and uniquely labeled

**Observation 2 — Nav landmark**:
1. The sidebar exposes a `<nav>` landmark
2. The nav landmark is uniquely labeled

---

### TC-FULL-001: End-to-end home dashboard lifecycle (HM-FULL)

**Preconditions**: Test user provisioned via backend admin API.

**Action**:
1. Authenticate via `loginViaUI` and land on `/home`
2. Assert welcome heading + subtitle + 4 stats cards + Quick Links heading + 6 card titles
3. Tab through all 6 quick-link cards verifying focus order
4. Press Enter on the focused Agents card
5. Press browser Back to return to `/home`
6. Click the Phone Numbers card
7. Press browser Back
8. Click the Settings card
9. Log out via the sidebar
10. Revisit `/home`

**Observation 1 — Step 2 — Initial render**:
1. h4 `Welcome to Tone` is visible
2. Subtitle is visible
3. All 4 stats cards render with their labels and values
4. h6 `Quick Links` is visible
5. All 6 quick-link card titles render

**Observation 2 — Step 3 — Tab order**:
1. Focus order is Agents → Phone Numbers → Analytics → Actions → Team Members → Settings

**Observation 3 — Steps 4–5 — Enter on Agents + Back**:
1. After Enter, URL is `/agents`
2. After Back, URL is `/home` with cards intact

**Observation 4 — Steps 6–7 — Phone Numbers**:
1. After click, URL is `/phone-numbers`
2. After Back, URL is `/home`

**Observation 5 — Step 8 — Settings**:
1. After click, URL is `/settings`

**Observation 6 — Steps 9–10 — Logout + revisit**:
1. After logout, URL redirects to `/auth/login`
2. Revisiting `/home` redirects to `/auth/login?redirect=%2Fhome`

**Cleanup**:
- Clear cookies and localStorage (no seeded data — page is hardcoded)

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-NAV-*` / `TC-LOADING-*` test case above)

- [x] Unauthenticated access → see TC-NAV-001
- [x] Expired token redirect → see TC-NAV-002
- [x] Redirect preserves `?redirect=%2Fhome` query param → see TC-NAV-001
- [x] Stats cards are non-interactive → see TC-EDGE-003
- [x] Two cards share the same `/settings` href → see TC-HAPPY-002
- [x] Rapid double-click does not duplicate navigation → see TC-EDGE-001
- [x] Cmd/Ctrl-click opens new tab → see TC-EDGE-002
- [x] New org sees zeroed stats → see TC-EDGE-004
- [x] Welcome heading hierarchy → see TC-EDGE-005
- [x] Offline load still renders → see TC-LOADING-001
- [x] Slow shell hydration → see TC-LOADING-002
- [x] Quick-link navigation after token expiry → see TC-ERROR-001
- [x] Home renders even when shell-level fetches fail → see TC-ERROR-002

---

## Business Rules

- Stats values are currently hardcoded (not fetched from API)
- Quick link cards use `next/link` for client-side navigation
- The page is a `'use client'` component (uses `useTheme()`)

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Heading hierarchy: h4 (Welcome) → h6 (Quick Links, card titles) → see TC-EDGE-005
- [x] Quick link cards rendered as `<a>` elements → covered in TC-A11Y-003
- [x] Tab navigation through quick link cards in DOM order → see TC-A11Y-001
- [x] Enter key activates focused quick link card → see TC-A11Y-002
- [x] Space key does NOT navigate (anchor semantics) → see TC-A11Y-003
- [x] Stats cards have no link role (correctly non-interactive) → see TC-A11Y-004
- [x] Card titles disambiguated from sidebar by full accessible name → covered in TC-A11Y-001
- [x] Main + Nav landmarks exposed → see TC-A11Y-005

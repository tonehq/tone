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

| Element | Type | Content / Label | Behavior |
|---------|------|-----------------|----------|
| Welcome heading | h4 | "Welcome to Tone" | Static text |
| Subtitle | body1 | "Build and deploy AI voice agents..." | Static text |
| Total Agents card | Card | label + "6" + "+2 this week" | Non-interactive |
| Active Calls card | Card | label + "0" + "Real-time" | Non-interactive |
| Minutes Used card | Card | label + "0" + "This month" | Non-interactive |
| Success Rate card | Card | label + "0%" + "Last 30 days" | Non-interactive |
| Quick Links heading | h6 | "Quick Links" | Static text |
| Agents card | Card (link) | icon + "Agents" + description | Navigates to `/agents` |
| Phone Numbers card | Card (link) | icon + "Phone Numbers" + description | Navigates to `/phone-numbers` |
| Analytics card | Card (link) | icon + "Analytics" + description | Navigates to `/analytics` |
| Actions card | Card (link) | icon + "Actions" + description | Navigates to `/actions` |
| Team Members card | Card (link) | icon + "Team Members" + description | Navigates to `/settings` |
| Settings card | Card (link) | icon + "Settings" + description | Navigates to `/settings` |

---

## Navigation

| Trigger | Destination | Condition |
|---------|-------------|-----------|
| Click Agents card | `/agents` | Always |
| Click Phone Numbers card | `/phone-numbers` | Always |
| Click Analytics card | `/analytics` | Always |
| Click Actions card | `/actions` | Always |
| Click Team Members card | `/settings` | Always |
| Click Settings card | `/settings` | Always |
| Enter key on focused card | Card's href | Always |
| No auth cookie | `/auth/login?redirect=%2Fhome` | Middleware redirect |

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

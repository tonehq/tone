# Feature Doc: <Page Name>

Feature documentation for test generation. Place in `e2e/docs/<page-name>.md`.
The `/generate-tests` skill auto-discovers docs matching the target page name,
or use `--docs e2e/docs/<page-name>.md` to specify explicitly.

---

## Page

- **Route**: `/route-path`
- **Component**: `src/app/.../ComponentName.tsx`
- **Auth required**: yes / no

---

## User Stories

### US-1: <Short title>
**As a** <user role>, **I want to** <action>, **so that** <outcome>.

**Acceptance criteria**:
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>

### US-2: <Short title>
...

---

## UI Elements

| Element | Type | Content / Label | Behavior |
|---------|------|-----------------|----------|
| Welcome heading | h4 | "Welcome to X" | Static text |
| Submit button | button | "Continue" | Submits form, shows loading |
| Email input | text input | placeholder: "Enter your email" | Required, email validation |

---

## Navigation

| Trigger | Destination | Condition |
|---------|-------------|-----------|
| Click "Continue" | `/home` | On success |
| Click "Sign up" link | `/auth/signup` | Always |
| No auth cookie | `/auth/login?redirect=<path>` | Middleware redirect |

---

## API Contracts

| Endpoint | Method | Request | Success Response | Error Response |
|----------|--------|---------|-----------------|----------------|
| `/auth/login` | POST | `{ email, password }` | `{ access_token, user_id, organizations }` | `{ detail: "..." }` |

---

## Edge Cases

- [ ] Empty form submission (required field validation)
- [ ] Network error during API call
- [ ] Expired auth token
- [ ] Very long input values
- [ ] Special characters in inputs

---

## Business Rules

- <rule 1>
- <rule 2>

---

## Accessibility Requirements

- [ ] All interactive elements reachable via keyboard
- [ ] Proper heading hierarchy (h1 > h2 > h3)
- [ ] Form inputs have associated labels
- [ ] Error messages announced to screen readers

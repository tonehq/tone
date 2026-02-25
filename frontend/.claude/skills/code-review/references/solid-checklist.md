# SOLID Checklist
<!-- Global Frontend Standard — framework notes are marked [React] [Next.js] -->
<!-- Severity: 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🔵 LOW -->

---

## 1. SRP — Single Responsibility Principle

> A module / component / function should have **one reason to change**.

### Violation signals

- 🟠 File mixes unrelated concerns: HTTP calls + domain rules + UI rendering in one place
- 🟠 [React] Component handles data fetching, business logic, **and** rendering — split into container + presentational, or use a custom hook
- 🟠 [Next.js] Page component does layout, data loading, and business logic — extract data-fetching to a Server Component or service layer
- 🟡 Function orchestrates many unrelated steps (validation → transform → persist → notify)
- 🟡 A single file has more than one exported component or class

### Detection question

> "If I describe this module in one sentence, do I use the word 'and'?"

```tsx
// ❌ Bad — one component owns fetch + transform + render
function UserCard({ id }: { id: string }) {
  const [user, setUser] = useState(null);
  useEffect(() => {
    fetch(`/api/users/${id}`)
      .then(r => r.json())
      .then(data => setUser({ ...data, fullName: `${data.first} ${data.last}` }));
  }, [id]);
  return <div>{user?.fullName}</div>;
}

// ✅ Good — fetch and transform in a hook; component only renders
function useUser(id: string) { /* fetch + transform */ }

function UserCard({ id }: { id: string }) {
  const { user } = useUser(id);
  return <div>{user?.fullName}</div>;
}
```

---

## 2. OCP — Open/Closed Principle

> Open for extension, closed for modification.

### Violation signals

- 🟠 Every new variant requires editing a growing `if/else` or `switch` block in core logic
- 🟠 [React] Adding a new UI variant means modifying the component instead of composing a new one
- 🟡 Feature flags scattered inside business logic with direct `if (flag)` branches
- 🟡 Rendering logic driven by a long list of boolean props (`showHeader`, `showFooter`, `showBadge`, …)

### Detection question

> "Can I add a new variant without touching existing code?"

```tsx
// ❌ Bad — every new type requires editing Button
function Button({ type }: { type: 'primary' | 'danger' | 'ghost' }) {
  if (type === 'primary') return <button className="btn-primary" />;
  if (type === 'danger')  return <button className="btn-danger" />;
}

// ✅ Good — compose without modifying
const variantClass = { primary: 'btn-primary', danger: 'btn-danger', ghost: 'btn-ghost' };

function Button({ variant, ...props }: { variant: keyof typeof variantClass }) {
  return <button className={variantClass[variant]} {...props} />;
}
```

---

## 3. LSP — Liskov Substitution Principle

> Any implementation of an abstraction must be substitutable without the caller knowing.

### Violation signals

- 🟠 A function or component checks the concrete type of a dependency to branch behavior
- 🟠 [React] A custom hook violates the documented contract of the hook it wraps (e.g., returns fewer fields, throws where the base never did)
- 🟡 An overriding implementation silently ignores required parameters
- 🟡 A child component throws or no-ops for props that the parent component handles correctly

### Detection question

> "Can I swap any implementation for another without the caller noticing?"

```tsx
// ❌ Bad — caller must inspect the concrete type
function render(repo: GitHubRepo | BitbucketRepo) {
  if (repo instanceof GitHubRepo) return repo.starCount;
  if (repo instanceof BitbucketRepo) return repo.watcherCount;
}

// ✅ Good — shared interface; caller is unaware of the concrete type
interface Repo { popularityCount: number }
function render(repo: Repo) { return repo.popularityCount; }
```

---

## 4. ISP — Interface Segregation Principle

> Consumers should not depend on members they do not use.

### Violation signals

- 🟠 [React] Component prop interface has 10+ fields; most callers pass only 2–3
- 🟠 A shared type forces consumers to provide irrelevant fields, often worked around with `Partial<>`
- 🟡 A service object is injected just to call one of its ten methods
- 🟡 `Pick<>` or `Omit<>` used heavily at call-sites — signal that the source type is too fat

### Detection question

> "Do all consumers use all members of this interface?"

```tsx
// ❌ Bad — callers only ever need name and avatar
interface User {
  id: string; name: string; avatar: string;
  billingAddress: string; subscriptionTier: string; // never used in UI
}

// ✅ Good — split by consumer need
interface UserProfile { name: string; avatar: string; }
interface UserBilling { billingAddress: string; subscriptionTier: string; }
```

---

## 5. DIP — Dependency Inversion Principle

> High-level modules must not depend on low-level modules. Both should depend on abstractions.

### Violation signals

- 🟠 Business logic directly imports a concrete HTTP client (`axios`, `fetch`) instead of a service abstraction
- 🟠 Direct reads from `localStorage`, `sessionStorage`, or `document.cookie` inside business-logic functions
- 🟠 [React] Custom hook hard-codes a specific store atom / Redux slice instead of accepting state via parameters or a context interface
- 🟡 Hard-coded environment-specific URLs or keys inside components
- 🟡 Test doubles are impossible without monkey-patching module internals

### Detection question

> "Can I swap the implementation (e.g., swap axios for fetch, or swap localStorage for an in-memory store) without changing the business logic?"

```tsx
// ❌ Bad — business logic coupled to axios directly
function useUser(id: string) {
  return useQuery(['user', id], () => axios.get(`/users/${id}`).then(r => r.data));
}

// ✅ Good — depends on an abstraction; implementation is injected or centralised
function useUser(id: string, fetcher = userService.getById) {
  return useQuery(['user', id], () => fetcher(id));
}
```

---

## Common Code Smells

| Smell | Severity | Signals | [React] Example |
|-------|----------|---------|-----------------|
| Long method | 🟠 | Function > 30 lines, multiple nesting levels | `useEffect` with 50+ lines of mixed logic |
| Feature envy | 🟡 | Module uses far more data from another module than from its own state | Component reaches into sibling store slice instead of receiving props |
| Primitive obsession | 🟡 | Raw `string`/`number` where a named type or enum would prevent invalid states | `status: string` instead of `status: 'idle' \| 'loading' \| 'error' \| 'success'` |
| Shotgun surgery | 🟠 | One business change requires edits across many unrelated files | Adding a field requires touching API type + atom + component + form + validator |
| Dead code | 🟡 | Unreachable branches, exported symbols with zero consumers | Flag always `false`, unused `variant` prop arm |
| Magic values | 🟡 | Hardcoded numbers/strings with no named constant | `setTimeout(fn, 3000)` — what is 3000? |
| Speculative generality | 🔵 | Abstractions built for hypothetical future use cases | `PluginManager` used by exactly one plugin |
| God component | 🟠 | [React] One component manages global layout, data, auth, and business rules | Dashboard page with 400+ lines |
| Prop drilling | 🟡 | [React] Prop passed through 3+ component layers unused in intermediaries | `userId` tunnelled through 4 components to reach a deeply nested avatar |

---

## Hook Design Principles [React]

- 🟠 A hook that fetches data **and** transforms **and** manages UI state violates SRP — split into `useQuery` + `useDerivedState`
- 🟠 A hook that directly imports a concrete store atom or global singleton cannot be tested in isolation (DIP violation)
- 🟡 Hook returns a giant object with 10+ fields — ISP violation; split into focused hooks
- 🟡 Hook name does not start with `use` — React rules of hooks enforcement breaks; always prefix
- 🟡 Hook accepts a callback without `useCallback` wrapping at the call-site — causes unnecessary re-runs

---

## Component Design Signals [React] [Next.js]

- 🟠 Component file > 250 lines — likely an SRP violation; split into sub-components or extract logic to hooks
- 🟠 Component accepts > 8 props — ISP signal; consider composition or a config object
- 🟡 Component renders different UIs based on `userRole` or `featureFlag` inline — extract to a strategy or render-prop pattern (OCP)
- 🟡 [Next.js] `'use client'` at the top of a file that only needs it for one small interactive child — push the boundary down, keep the parent as a Server Component (SRP + performance)
- 🔵 Default export and named export of the same component in the same file — unnecessary duplication

---

## Refactor Heuristics

| # | Heuristic | Principle addressed |
|---|-----------|-------------------|
| 1 | Split by **responsibility**, not by size | SRP |
| 2 | Introduce abstraction only at the **second use case** — resist the urge to generalise early | OCP, YAGNI |
| 3 | Keep refactors **incremental** — isolate behaviour before moving it | All |
| 4 | Prefer **composition over inheritance** — wrap, don't extend | LSP, OCP |
| 5 | Make **illegal states unrepresentable** via TypeScript union types | ISP, SRP |
| 6 | [React] Extract logic to a **custom hook** before extracting to a new component | SRP |
| 7 | [React] Pass **data and callbacks as props** rather than importing global state inside a component | DIP |
| 8 | Depend on **interfaces / abstract types**, not on concrete implementations | DIP |

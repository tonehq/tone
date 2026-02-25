# Code Quality Checklist
<!-- Global Frontend Standard — framework notes are marked [React] [Next.js] [Vue] etc. -->
<!-- Severity: 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🔵 LOW -->

---

## 1. Error Handling

### Anti-patterns

```javascript
try { ... } catch (e) { }                 // 🔴 CRITICAL — silent failure, swallows all errors
try { ... } catch (e) { console.log(e) }  // 🟠 HIGH — log-and-forget, no recovery or user feedback
.then(fn).catch(() => {})                 // 🟠 HIGH — swallowed rejection in promise chain
```

### Checklist

- 🔴 Empty `catch` block — state/UI silently not updated, data loss risk
- 🟠 Missing `try/catch` around network calls (HTTP, WebSocket, fetch/axios)
- 🟠 Unhandled promise rejections — missing `.catch()` or `await` without try/catch
- 🟠 [React] No `ErrorBoundary` wrapping async-loaded or data-driven subtrees
- 🟡 `catch (e)` used without narrowing the type — always check `e instanceof Error` before accessing `.message`
- 🟡 `finally` block with a `return` statement — silently discards the thrown error or resolved value
- 🟡 Error messages shown to users that expose internal stack traces or API details
- 🟡 [State mgmt] Write atoms / store actions with async calls but no error rollback
- 🔵 Generic `"Something went wrong"` with no actionable guidance for the user

```typescript
// ✅ Correct pattern
try {
  const data = await fetchUser(id);
  setState(data);
} catch (err) {
  const message = err instanceof Error ? err.message : 'Unknown error';
  console.log(err);  // logging is fine here for debugging
  setError(message); // also surface to UI so the user sees it
} finally {
  setLoading(false); // never put return here
}
```

---

## 2. TypeScript Quality

### Checklist

- 🔴 `as any` or `@ts-ignore` without an explaining comment — masks real type errors
- 🟠 Non-null assertion `!` on values that can genuinely be `null`/`undefined` at runtime
- 🟠 `as ConcreteType` casts without a runtime guard — lies to the compiler, crashes at runtime
- 🟡 `object`, `{}`, or `Function` as a type — too broad, provides no safety
- 🟡 Missing return types on exported functions — callers cannot rely on the contract
- 🟡 `interface` vs `type` used inconsistently within the same codebase (pick one convention)
- 🟡 Enums used where a string union type is cleaner and tree-shakeable
- 🔵 Overly wide union types (`string | number | boolean | object`) — usually indicates a design issue

```typescript
// 🔴 Bad
const user = response.data as User;
user.profile!.name;

// ✅ Good
function isUser(v: unknown): v is User {
  return typeof v === 'object' && v !== null && 'id' in v;
}
if (isUser(response.data)) { /* safe */ }
```

---

## 3. Boundary Conditions

### Dangerous patterns

```typescript
const name = user.profile.name   // 🔴 no null/undefined guard on nested access
const first = items[0].id        // 🟠 unchecked array access — crashes on empty array
const avg = total / count        // 🟠 division without zero-guard → NaN / Infinity
if (value) { ... }               // 🟡 hides falsy values: 0, "", false, NaN
const n = parseInt(str)          // 🟡 returns NaN — never passed directly to arithmetic
```

### Checklist

- 🔴 Deep property access without optional chaining (`?.`) or null guard
- 🟠 Array index access `[0]`, `[n]` without length check
- 🟠 Division or modulo without a zero-denominator guard
- 🟠 `NaN` propagation — arithmetic on unvalidated user input silently produces `NaN`
- 🟡 `if (value)` guards that incorrectly exclude `0`, `""`, or `false` as valid states
- 🟡 Empty-state handling missing on lists, tables, and data-driven UIs (show placeholder, not blank)
- 🟡 Async data accessed before the loading state resolves — missing loading/skeleton guard
- 🟡 Date arithmetic without validating that both operands are valid `Date` objects
- 🔵 `parseInt` / `parseFloat` result used without `Number.isNaN()` check

---

## 4. Performance

### React / Component-based frameworks [React]

- 🟠 Expensive computations inside render without memoisation (`useMemo`)
- 🟠 Inline object/array literals or anonymous functions as props — new reference each render, breaks `memo`
- 🟠 Missing `useCallback` on event handlers passed to memoised child components
- 🟡 `React.memo` absent on pure leaf components receiving stable props
- 🟡 Context API value object recreated on every render — split context or memoize the value
- 🟡 Large lists rendered without virtualisation (`react-window`, `tanstack-virtual`, etc.)
- 🟡 Heavy event handlers (scroll, resize, keypress, input) without debounce or throttle
- 🔵 `useReducer` or external state used where local `useState` is sufficient

### Next.js / SSR frameworks [Next.js]

- 🟠 `'use client'` placed too high — forces entire subtree to client bundle unnecessarily
- 🟠 Raw `<img>` instead of `<Image>` from `next/image` — misses lazy-load and size optimisation
- 🟡 Fetch inside a Client Component that could be a Server Component with no interactivity
- 🟡 `getServerSideProps` (Pages Router) or Server Action fetching data that rarely changes — prefer `getStaticProps` + revalidation

### Bundle & Loading

- 🟠 Importing entire libraries when only one function is needed (e.g., `import _ from 'lodash'` instead of `import debounce from 'lodash/debounce'`)
- 🟡 Dynamic `import()` missing for large, route-specific components
- 🟡 Third-party scripts loaded synchronously in `<head>` — use `async`/`defer` or framework equivalents
- 🔵 Duplicate dependencies or multiple versions of the same library in the bundle

### State Management (framework-agnostic)

- 🟠 Sequential `await` calls that are independent — use `Promise.all` / `Promise.allSettled`
- 🟡 Global state updated for data that is only needed in one component — prefer local state
- 🟡 Store subscriptions that trigger full re-render on unrelated slice changes — use selectors
- 🟡 Optimistic updates without rollback on API failure

---

## 5. Naming & Readability

- 🟡 Boolean variables / props not prefixed with `is`, `has`, `can`, `should` (e.g., `loading` → `isLoading`)
- 🟡 Functions named with nouns instead of verbs (`userFetch` → `fetchUser`)
- 🟡 Generic names with no domain meaning: `data`, `info`, `temp`, `obj`, `val`, `res`
- 🟡 Abbreviations that are not universally understood (`usrPrfl` → `userProfile`)
- 🟡 Inconsistent case conventions in the same file (camelCase mixed with snake_case)
- 🔵 Comments that describe *what* the code does instead of *why* it does it
- 🔵 Commented-out code committed to the repo — use version control instead

---

## 6. Code Duplication & Structure

- 🟠 Copy-pasted logic in 3+ places — extract a shared utility or hook
- 🟡 Component files exceeding ~250 lines or functions exceeding ~40 lines — split by responsibility
- 🟡 JSX nesting deeper than 4 levels — extract sub-components
- 🟡 Prop drilling through 3+ component levels — consider context, composition, or state management
- 🟡 Magic numbers/strings without named constants (`setTimeout(fn, 3000)` → `const DEBOUNCE_MS = 3000`)
- 🔵 Speculative abstractions built for hypothetical future use cases — YAGNI

---

## 7. Dead Code

- 🟡 Unused imports — confirmed by linting (ESLint `no-unused-vars`)
- 🟡 Exported functions/components with zero consumers in the codebase
- 🟡 Feature-flag–gated code where the flag is always `true` or always `false`
- 🟡 `TODO` / `FIXME` comments older than one release cycle without a linked issue
- 🔵 `console.log` / `console.debug` left in production code paths

---

## 8. Async & Concurrency

- 🔴 `async` function called without `await` and without `.catch()` — fire-and-forget that swallows errors
- 🟠 Race condition: stale closure captures outdated state inside `useEffect` or event listener
- 🟠 Missing cleanup / cancellation for async operations on unmounted components (`AbortController`, effect cleanup)
- 🟡 `Promise.all` used where `Promise.allSettled` is needed — one rejection cancels all
- 🟡 Async operations initiated inside loops — use `Promise.all(items.map(...))` not `for...of` with sequential `await`

```typescript
// 🔴 Bad — fire-and-forget, no error surface
saveUser(data);

// 🟠 Bad — sequential when independent
const users = await fetchUsers();
const orgs  = await fetchOrgs();   // waits for users unnecessarily

// ✅ Good
const [users, orgs] = await Promise.all([fetchUsers(), fetchOrgs()]);
```

---

## 9. Accessibility (mandatory)

- 🔴 Interactive elements (`div`, `span`) with `onClick` but no `role` or keyboard handler — use `<button>` or `<a>`
- 🟠 `<img>` without `alt` attribute, or `alt=""` on informational images
- 🟠 Form inputs without associated `<label>` or `aria-label`
- 🟡 Heading hierarchy skipped (e.g., `h1` → `h3`, no `h2`)
- 🟡 Missing `aria-live` on dynamically updated content (alerts, toasts, status messages)
- 🟡 Focus not trapped in modals / drawers — user can tab into background content
- 🟡 Colour contrast below WCAG AA ratio (4.5:1 for normal text)
- 🔵 Missing `aria-expanded`, `aria-controls` on accordion / disclosure patterns

---

## Severity Reference

| Severity | Action |
|----------|--------|
| 🔴 CRITICAL | Block merge — data loss, crash, or security risk |
| 🟠 HIGH | Fix before merge — correctness or significant UX degradation |
| 🟡 MEDIUM | Fix in same PR or create a tracked issue |
| 🔵 LOW | Suggestion — address opportunistically |

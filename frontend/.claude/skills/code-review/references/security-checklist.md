# Security and Reliability Checklist

<!-- Global Frontend Standard — React + Next.js -->
<!-- Framework notes are marked [React] [Next.js] -->

---

## Risk Classification

| Level | Label    | Meaning                                                     |
| ----- | -------- | ----------------------------------------------------------- |
| 🔴    | Critical | Exploitable or high-impact security flaw — block merge      |
| 🟡    | Moderate | Risky pattern that must be fixed before release             |
| 🔵    | Low      | Improvement recommended — address in current or next sprint |
| ⚪    | No Issue | Checked and clear                                           |

When uncertain → choose the safer (higher) classification.

---

## Input Mode

- **diff mode**: Analyze only added or modified code. Do not assume visibility of unchanged files. Mark findings that need broader context as `"Requires Full Review"`.
- **full mode**: Analyze full repository context.

---

## Finding Format

Use this block for every finding in every section:

```
- [RISK LEVEL] Short description of the vulnerability
  - **Location**: `path/to/file.tsx:line`
  - **Exploit scenario**: How an attacker would trigger this in practice
  - **Impact**: What data or system is at risk
  - **Recommendation**: Concrete fix
```

If no findings in a section, write the "If none detected" statement verbatim.

---

## 1. Input / Output Safety

### Detection signals — look for these patterns

| Pattern                                                      | Risk                   | Notes                                                    |
| ------------------------------------------------------------ | ---------------------- | -------------------------------------------------------- |
| `dangerouslySetInnerHTML`                                    | 🔴 XSS                 | Any user-controlled value injected here is exploitable   |
| `innerHTML =` / `outerHTML =`                                | 🔴 XSS                 | Direct DOM write; bypasses React's escaping              |
| Template literals with user input rendered as HTML           | 🔴 XSS                 | `\`<div>${userInput}</div>\`` passed to a DOM API        |
| URL parameters injected into the DOM without encoding        | 🟡 XSS                 | `searchParams.get('q')` rendered unescaped               |
| `JSON.parse` on untrusted / external data without validation | 🟡 Injection           | Malformed payload can throw or poison state              |
| `fetch` / `axios` called with a user-controlled URL          | 🟡 SSRF                | No allowlist → attacker can probe internal services      |
| `Object.assign({}, userInput)` / deep merge with user data   | 🟡 Prototype pollution | `__proto__` key in input can corrupt the prototype chain |
| SQL / NoSQL query built by string concatenation              | 🔴 Injection           | Always use parameterised queries                         |
| `eval()`, `new Function()`, `setTimeout(string)`             | 🔴 Code injection      | Never pass strings to execution primitives               |

### Findings

_(One block per finding, or:)_
"No immediate input/output vulnerabilities detected."

---

## 2. Authentication / Authorization

### Detection signals — look for these patterns

| Pattern                                                                  | Risk                     | Notes                                                                      |
| ------------------------------------------------------------------------ | ------------------------ | -------------------------------------------------------------------------- |
| Page / route without auth guard                                          | 🔴 AuthN bypass          | [Next.js] Must be covered by `middleware.ts` or a layout-level guard       |
| [Next.js] New route not protected in `middleware.ts`                     | 🔴 AuthN bypass          | Every new `app/` or `pages/` route must be explicitly included or excluded |
| API call without Authorization header                                    | 🔴 AuthZ bypass          | Backend must not trust unauthenticated requests                            |
| Role or permission derived from a query param or client input            | 🔴 Privilege escalation  | Role must come from server-validated session, not from `?role=admin`       |
| IDOR: route param used as an object ID without ownership check           | 🔴 Broken access control | `/users/:id` readable by any authenticated user                            |
| Client-side-only `if (isAdmin)` guard with no server enforcement         | 🟡 AuthZ bypass          | JS can be modified; server must enforce the same rule                      |
| Trusting `localStorage` / cookie value as an authoritative identity      | 🟡 Identity spoofing     | Must be validated server-side on every request                             |
| Exposure of protected content in initial HTML before auth check resolves | 🔵 Info disclosure       | Use SSR auth check or show skeleton until auth is confirmed                |

### Findings

_(One block per finding, or:)_
"No authentication or authorization vulnerabilities detected in reviewed scope."

---

## 3. Secrets and PII Exposure

### Detection signals — look for these patterns

| Pattern                                                                   | Risk               | Notes                                                                   |
| ------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------- |
| Hardcoded API key, token, or password in source                           | 🔴 Secret exposure | Even in private repos; rotate immediately if found                      |
| `NEXT_PUBLIC_*` env var holding a secret                                  | 🔴 Secret exposure | All `NEXT_PUBLIC_` vars are embedded in the browser bundle              |
| Token stored in `localStorage` or `sessionStorage`                        | 🟡 Token theft     | Accessible to any JS on the page (XSS pivot); prefer `HttpOnly` cookies |
| Sensitive data (PII, tokens) held in global/serializable state            | 🟡 Exposure risk   | Global state can be inspected via devtools; avoid storing raw tokens    |
| `console.log` / `console.debug` printing tokens, passwords, or user PII   | 🟡 Info disclosure | Visible in browser devtools and third-party monitoring tools            |
| Unmasked PII (email, phone, SSN) rendered in UI without masking           | 🔵 PII exposure    | Mask by default; reveal only on deliberate user action                  |
| Sensitive cookies without `HttpOnly` + `Secure` + `SameSite=Strict` flags | 🟡 Cookie theft    | Readable by JS or sent cross-origin without these flags                 |

### Findings

_(One block per finding, or:)_
"No exposed secrets or PII risks detected."

---

## 4. Runtime Risks

### Detection signals — look for these patterns

| Pattern                                                                      | Risk              | Notes                                                                      |
| ---------------------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------- |
| Infinite loop — `while(true)` or recursive call with no base case            | 🔴 DoS / crash    | Blocks the main thread or causes a stack overflow                          |
| Unbounded array / object growing in global state                             | 🟡 Memory leak    | State never pruned; grows until tab crashes                                |
| `fetch` / `axios` call with no timeout configured                            | 🟡 Hang risk      | Request can hang indefinitely; set `timeout` option                        |
| Missing `AbortController` / request cancellation on unmount                  | 🟡 Memory leak    | [React] Async response arrives after unmount, sets state on dead component |
| Event listener attached without cleanup (`removeEventListener`)              | 🟡 Memory leak    | [React] Must be removed in `useEffect` cleanup function                    |
| Regex with catastrophic backtracking — nested quantifiers on unbounded input | 🟡 ReDoS          | `/(a+)+$/` on long strings can hang the thread                             |
| Polling interval with no upper bound or kill switch                          | 🔵 Resource drain | Always pair with a max-retry or circuit-breaker                            |
| Unbounded retry loop on network failure                                      | 🟡 DoS risk       | Use exponential back-off with a maximum retry count                        |

### Findings

_(One block per finding, or:)_
"No runtime stability risks detected."

---

## 5. Race Conditions

### Detection signals — look for these patterns

| Pattern                                                                       | Risk                  | Notes                                                                |
| ----------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------- |
| Check-then-act on auth state: `if (isAuth) doAction()`                        | 🔴 TOCTOU             | Auth state can change between check and act                          |
| Multiple concurrent writes to the same state slice without coordination       | 🟡 State corruption   | Last writer wins; intermediate state is lost                         |
| Optimistic UI update with no rollback on API failure                          | 🟡 Inconsistent state | UI shows success; server state is actually unchanged                 |
| Stale closure: async callback captures a variable that changes before it runs | 🟡 Stale data         | [React] `useEffect` or `setTimeout` callback reads old state         |
| `useEffect` with async operation and no cleanup / cancellation                | 🟡 Race condition     | [React] Slow first request resolves after fast second; old data wins |
| Parallel form submissions with no in-flight guard                             | 🔵 Duplicate write    | User double-clicks; two identical mutations sent                     |

```tsx
// ❌ Dangerous — check-then-act; state may change between lines
if (user.balance >= amount) {
  user.balance -= amount; // balance could have changed
}

// ✅ Safe — atomic operation enforced server-side; optimistic update with rollback
```

### Findings

_(One block per finding, or:)_
"No race condition patterns detected."

---

## 6. Data Integrity

### Detection signals — look for these patterns

| Pattern                                                             | Risk                    | Notes                                                                      |
| ------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------- |
| Partial state update leaving related fields inconsistent            | 🟡 Inconsistent state   | e.g. `user.name` updated but `user.displayName` is stale                   |
| Optimistic update with no error rollback path                       | 🟡 Data loss            | API fails silently; UI and server are out of sync                          |
| Direct mutation of objects held in state                            | 🟡 Unpredictable render | `state.items.push(x)` — React does not detect the change                   |
| State transition with no explicit `loading → success / error` model | 🔵 UI inconsistency     | Missing states allow invalid combinations (loading + error simultaneously) |
| Retry logic without idempotency key                                 | 🟡 Duplicate write      | Retried POST creates duplicate records if server has no idempotency guard  |
| Inconsistent state across related stores / atoms on partial failure | 🟡 Data desync          | Module A updated, Module B not — downstream reads see torn state           |

### Findings

_(One block per finding, or:)_
"No data integrity risks detected."

---

## Summary Risk Level

Report one overall level after completing all sections:

| Overall Level  | Condition                                              |
| -------------- | ------------------------------------------------------ |
| 🔴 High Risk   | Any 🔴 Critical finding present                        |
| 🟡 Medium Risk | No Critical findings; one or more 🟡 Moderate findings |
| 🟢 Low Risk    | No Critical or Moderate findings; Low / No Issue only  |

> **Diff mode note**: Assessment limited to modified code only. Findings marked `"Requires Full Review"` need whole-repo context before final classification.

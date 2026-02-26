# Performance Checklist

<!-- Global Frontend Standard — React + Next.js -->
<!-- Framework notes are marked [React] [Next.js] -->

---

## Severity Classification

| Level | Label    | Meaning                                                                    |
| ----- | -------- | -------------------------------------------------------------------------- |
| 🔴    | Critical | Measurable user-facing regression — blocks on slow devices / slow networks |
| 🟠    | High     | Significant perf debt — fix before merge                                   |
| 🟡    | Medium   | Noticeable in profiling — fix in current or next sprint                    |
| 🔵    | Low      | Minor optimisation — address opportunistically                             |

When uncertain → choose the safer (higher) classification.

---

## Input Mode

- **diff mode**: Analyze only added or modified code. Mark findings that need broader bundle/profiling context as `"Requires Full Review"`.
- **full mode**: Analyze full repository context.

---

## Finding Format

Use this block for every finding in every section:

```
- [SEVERITY] Short description
  - **Location**: `path/to/file.tsx:line`
  - **Impact**: Which metric or user experience is hurt (render time / LCP / CLS / bundle size / etc.)
  - **How to detect**: DevTools panel or command to confirm the problem
  - **Recommendation**: Concrete fix with code direction
```

If no findings in a section, write the "If none detected" statement verbatim.

---

## 1. React Rendering Performance [React]

### Detection signals

| Pattern                                                                             | Severity | Notes                                                                            |
| ----------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------- |
| Expensive calculation inside render body without `useMemo`                          | 🟠       | Recalculates on every render regardless of input changes                         |
| Inline object / array / function literal passed as a prop                           | 🟠       | New reference each render — breaks `React.memo` and causes child re-render       |
| Missing `useCallback` on handler passed to a memoised child                         | 🟠       | Child re-renders every time parent renders, defeating `memo`                     |
| `React.memo` absent on pure leaf component with stable props                        | 🟡       | Renders on every parent update even when props are unchanged                     |
| Context value object created inline without `useMemo`                               | 🟠       | Every context consumer re-renders on every provider render                       |
| Context with mixed fast-changing + slow-changing state in one Provider              | 🟡       | Split into separate contexts — one change re-renders all consumers               |
| Large flat list rendered without virtualisation                                     | 🟠       | Hundreds of DOM nodes mounted at once; use `react-window` or `@tanstack/virtual` |
| `useEffect` dependency array missing a dependency                                   | 🔴       | Stale closure — component behaves incorrectly and is hard to debug               |
| `useEffect` dependency array with an object / array that is recreated each render   | 🟠       | Effect fires every render; stabilise the dependency with `useMemo` / `useRef`    |
| Heavy event handler (scroll, resize, input, mousemove) without debounce or throttle | 🟡       | Fires hundreds of times per second; throttle to ≤ 60 fps                         |
| Derived state recalculated in render from props without `useMemo`                   | 🟡       | Recalculates on every render even when inputs haven't changed                    |
| Reconciliation of deeply nested component trees on shallow state changes            | 🟡       | Flatten state or use selectors to limit re-render scope                          |

```tsx
// ❌ Bad — new object reference every render, breaks memo on child
<Chart config={{ color: 'red', size: 12 }} onHover={() => setHovered(true)} />;

// ✅ Good — stable references
const chartConfig = useMemo(() => ({ color: 'red', size: 12 }), []);
const handleHover = useCallback(() => setHovered(true), []);
<Chart config={chartConfig} onHover={handleHover} />;
```

### Findings

_(One block per finding, or:)_
"No React rendering performance issues detected."

---

## 2. Next.js & SSR Performance [Next.js]

### Detection signals

| Pattern                                                                              | Severity | Notes                                                                                   |
| ------------------------------------------------------------------------------------ | -------- | --------------------------------------------------------------------------------------- |
| `'use client'` at the top of a file that only needs interactivity in one small child | 🟠       | Pushes entire subtree into client bundle; move boundary to the leaf component           |
| Raw `<img>` instead of `<Image>` from `next/image`                                   | 🟠       | No lazy-load, no format negotiation, no size optimisation                               |
| Server Component making sequential `await` fetches that are independent              | 🟠       | Use `Promise.all` — sequential fetches add latency equal to the sum of all requests     |
| Missing `<Suspense>` boundary around async Server Components                         | 🟡       | Page blocks until all data resolves; Suspense enables streaming partial HTML            |
| Missing `loading.tsx` for slow routes                                                | 🟡       | No skeleton shown during navigation; user sees blank page                               |
| `generateMetadata` making a separate blocking API call already made in the page      | 🟡       | Deduplicate with `cache()` or pass data down                                            |
| SSR (`getServerSideProps` / Server Component) fetching data that rarely changes      | 🟡       | Prefer ISR (`revalidate`) or `force-cache` — avoid per-request fetch for static content |
| Client Component fetching data that could be fetched in a Server Component           | 🟡       | Server fetch eliminates waterfall; client fetch adds a round-trip                       |
| `next/font` not used for custom fonts — raw `@import` in CSS instead                 | 🔵       | `next/font` eliminates CLS from font swap and self-hosts the font                       |
| Missing `prefetch` on high-probability navigation links                              | 🔵       | `<Link prefetch>` preloads the page; add for primary CTAs                               |

```tsx
// ❌ Bad — sequential fetches in Server Component
const user = await fetchUser(id);
const orders = await fetchOrders(id); // waits for user unnecessarily

// ✅ Good — parallel
const [user, orders] = await Promise.all([fetchUser(id), fetchOrders(id)]);
```

### Findings

_(One block per finding, or:)_
"No Next.js rendering or SSR performance issues detected."

---

## 3. Bundle & Code Splitting

### Detection signals

| Pattern                                                                             | Severity | Notes                                                                           |
| ----------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------- |
| Full library import where only one function is needed                               | 🟠       | `import _ from 'lodash'` pulls the entire library; import the specific function |
| Large component / page not wrapped in `dynamic()` / `React.lazy`                    | 🟠       | Ships code for all routes in the initial bundle                                 |
| No route-level code splitting in a growing SPA                                      | 🟡       | Initial JS payload grows with every new page                                    |
| Duplicate package versions in `node_modules` (check `yarn why` / `npm ls`)          | 🟡       | Two versions of React or a utility ship to the browser simultaneously           |
| Third-party script loaded via `<script src>` in `<head>` without `async` or `defer` | 🟠       | Blocks HTML parsing; use `next/script` strategy or `async`/`defer` attribute    |
| Missing bundle analyser in CI — bundle size not tracked                             | 🔵       | Size regressions go undetected; add `@next/bundle-analyzer` or `bundlesize`     |
| `moment.js` imported without tree-shaking locale restriction                        | 🟠       | Adds ~300 KB gzip; migrate to `date-fns` or `dayjs`                             |
| Icons imported from a full icon pack rather than individual files                   | 🟡       | `import { Icon } from 'react-icons'` pulls all icons; import the specific icon  |

```tsx
// ❌ Bad — entire library in initial bundle
import _ from 'lodash';

// ✅ Good — tree-shaken single function
import debounce from 'lodash/debounce';

// ✅ Good — route-level split
const HeavyChart = dynamic(() => import('./HeavyChart'), { ssr: false });
```

### Findings

_(One block per finding, or:)_
"No bundle size or code splitting issues detected."

---

## 4. Network & API Efficiency

### Detection signals

| Pattern                                                                        | Severity | Notes                                                                            |
| ------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------- |
| N+1 fetch pattern — one request per list item inside a loop or `map`           | 🔴       | 100 items = 100 sequential requests; batch or use a bulk endpoint                |
| Independent API calls fired sequentially instead of in parallel                | 🟠       | Use `Promise.all` / `Promise.allSettled`; removes additive latency               |
| Large dataset fetched in full with no pagination or infinite scroll            | 🟠       | Initial payload grows with data volume; always paginate server-side              |
| API response not cached — same data refetched on every navigation              | 🟡       | Use HTTP cache headers, SWR, React Query, or Next.js `fetch` cache               |
| Missing stale-while-revalidate strategy for frequently-accessed endpoints      | 🟡       | User waits for fresh data on every visit; SWR shows stale instantly then updates |
| No request deduplication — same endpoint called by multiple sibling components | 🟡       | React Query / SWR deduplicate in-flight requests automatically                   |
| Missing `AbortController` — stale request resolves after a newer one           | 🟡       | Old response overwrites new data; cancel on `useEffect` cleanup                  |
| Over-fetching — entire resource returned when only a few fields are needed     | 🔵       | Use field selection, GraphQL fragments, or a slimmer endpoint                    |
| Polling interval with no back-off or circuit-breaker when tab is hidden        | 🟡       | Fires even when user is not looking; pause with `document.visibilityState`       |

```tsx
// ❌ Bad — N+1
const details = await Promise.all(ids.map((id) => fetch(`/items/${id}`)));

// ✅ Good — single bulk request
const details = await fetch(`/items/bulk?ids=${ids.join(',')}`);

// ✅ Good — cancel stale request
useEffect(() => {
  const controller = new AbortController();
  fetchUser(id, { signal: controller.signal }).then(setUser);
  return () => controller.abort();
}, [id]);
```

### Findings

_(One block per finding, or:)_
"No network or API efficiency issues detected."

---

## 5. Core Web Vitals

### LCP — Largest Contentful Paint (target: ≤ 2.5 s)

| Pattern                                                                      | Severity | Notes                                                            |
| ---------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------- |
| Hero image not preloaded — browser discovers it late in render               | 🔴       | Add `<link rel="preload">` or `priority` prop on `next/image`    |
| LCP image served in JPEG/PNG instead of WebP / AVIF                          | 🟠       | Modern formats are 30–50% smaller at equal quality               |
| LCP element is text blocked by a render-blocking web font                    | 🟠       | Use `font-display: swap` and `next/font` preloading              |
| Server response time (TTFB) > 600 ms                                         | 🟠       | SSR bottleneck; cache the response or move static content to CDN |
| LCP image has no explicit `width` / `height` — triggers layout recalculation | 🟡       | Always declare dimensions to allow browser to reserve space      |

### INP — Interaction to Next Paint (target: ≤ 200 ms)

| Pattern                                                                       | Severity | Notes                                                             |
| ----------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| Long task (> 50 ms) on the main thread blocks input response                  | 🔴       | Break up with `scheduler.yield()`, `setTimeout(0)`, or Web Worker |
| State update on every keystroke without debounce triggers expensive re-render | 🟠       | Debounce input handlers or use uncontrolled input with `ref`      |
| Click handler performing synchronous heavy computation before visual feedback | 🟠       | Show optimistic UI immediately; move work off the critical path   |
| Third-party script monopolising the main thread during interaction            | 🟡       | Audit with Chrome DevTools Performance panel; defer or sandbox    |

### CLS — Cumulative Layout Shift (target: ≤ 0.1)

| Pattern                                                                      | Severity | Notes                                                                  |
| ---------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------- |
| Image or video without `width` / `height` attributes — shifts layout on load | 🔴       | Always declare dimensions; use `aspect-ratio` CSS as fallback          |
| Font swap causing text reflow — FOUT / FOIT                                  | 🟠       | Use `next/font` or `font-display: optional` to eliminate shift         |
| Dynamic content injected above existing content (ads, banners, toasts)       | 🟠       | Reserve space with a min-height placeholder before content loads       |
| Skeleton / loading state with different dimensions than real content         | 🟡       | Skeleton must match the final layout dimensions exactly                |
| CSS animation using `top` / `left` / `margin` instead of `transform`         | 🟡       | Non-composite properties trigger layout; use `transform` and `opacity` |

### Findings

_(One block per finding per metric, or:)_
"No Core Web Vitals regressions detected."

---

## 6. Memory Management

### Detection signals

| Pattern                                                                         | Severity | Notes                                                                           |
| ------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------- |
| `addEventListener` inside `useEffect` without `removeEventListener` in cleanup  | 🟠       | Listener accumulates on every mount; leaks memory and causes duplicate handlers |
| `setInterval` / `setTimeout` not cleared in `useEffect` cleanup                 | 🟠       | Timer fires after component unmount; `setState` on dead component               |
| Async fetch result applied to state after component unmount                     | 🟡       | Use `AbortController` or an `isMounted` flag in cleanup                         |
| Large array / object stored in global state and never pruned                    | 🟡       | Grows unbounded; eventually crashes the tab                                     |
| Closure inside an event handler retaining a reference to a large object         | 🟡       | Object cannot be garbage-collected while handler lives                          |
| `IntersectionObserver` / `ResizeObserver` / `MutationObserver` not disconnected | 🟡       | Observer holds a ref to the DOM node; prevents GC                               |
| Canvas 2D context or WebGL resources not released on unmount                    | 🟡       | GPU memory leak; critical on pages that mount/unmount the canvas frequently     |

```tsx
// ✅ Correct cleanup pattern
useEffect(() => {
  const handler = (e: Event) => {
    /* ... */
  };
  window.addEventListener('resize', handler);
  const id = setInterval(tick, 1000);
  return () => {
    window.removeEventListener('resize', handler);
    clearInterval(id);
  };
}, []);
```

### Findings

_(One block per finding, or:)_
"No memory management issues detected."

---

## 7. State Management Performance

### Detection signals

| Pattern                                                                          | Severity | Notes                                                                                       |
| -------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| Global store / atom used for data that is local to one component                 | 🟡       | Pollutes global state, causes unrelated components to re-render; use local `useState`       |
| Store subscription without a selector — component re-renders on any slice change | 🟠       | Subscribe only to the slice needed; use `useSelector(selector)` or atom primitives          |
| Derived / computed value recalculated in the store on every update               | 🟡       | Memoize derived values with a selector or `useMemo`                                         |
| Multiple rapid state updates that could be batched into one                      | 🟡       | React 18 auto-batches in async; for earlier or external code, use `unstable_batchedUpdates` |
| Optimistic update re-renders twice — once on action, once on API response        | 🔵       | Normalise the store shape to avoid double reconciliation                                    |
| Store holds raw API response objects instead of normalised entities              | 🔵       | Denormalised data causes cascading updates when one entity appears in multiple places       |

### Findings

_(One block per finding, or:)_
"No state management performance issues detected."

---

## 8. Asset & CSS Performance

### Detection signals

| Pattern                                                                             | Severity | Notes                                                                           |
| ----------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------- |
| Uncompressed / unoptimised raster images (> 200 KB on a UI element)                 | 🟠       | Compress with Squoosh / Sharp; convert to WebP; serve via CDN                   |
| CSS animation using `top`, `left`, `width`, `margin` — triggers layout              | 🟡       | Use `transform` and `opacity` — both are GPU-composited and do not cause layout |
| Large global stylesheet imported everywhere — unused rules on most pages            | 🟡       | Scope CSS to routes; use CSS Modules or `@layer` to limit global scope          |
| Render-blocking `<link rel="stylesheet">` for a non-critical stylesheet             | 🟡       | Load non-critical CSS with `media="print" onload="this.media='all'"` pattern    |
| Inline `style` prop with dynamic values causing style recalculation on every render | 🔵       | Prefer CSS classes toggled by className; inline style recalculates paint        |
| SVG icons embedded as `<img src>` instead of inline or as a component               | 🔵       | Inline SVG allows CSS theming and eliminates an extra HTTP request              |
| `background-image` used for content images                                          | 🔵       | Content images belong in `<img>` / `<Image>` for LCP tracking and accessibility |

### Findings

_(One block per finding, or:)_
"No asset or CSS performance issues detected."

---

## Summary Performance Assessment

Report one overall level after completing all sections:

| Level                                | Condition                                    |
| ------------------------------------ | -------------------------------------------- |
| 🔴 Critical — Fix before release     | Any 🔴 finding present                       |
| 🟠 High — Fix before merge           | No Critical; one or more 🟠 findings         |
| 🟡 Medium — Schedule for next sprint | No Critical or High; one or more 🟡 findings |
| 🟢 No significant issues             | Only 🔵 Low findings or none                 |

> **Diff mode note**: Assessment limited to modified code only. Findings marked `"Requires Full Review"` need bundle analysis or profiling to confirm.

---

## Profiling Tools Reference

| Tool                                | What it measures                                         |
| ----------------------------------- | -------------------------------------------------------- |
| Chrome DevTools → Performance panel | Long tasks, main-thread blocking, frame rate             |
| Chrome DevTools → Memory panel      | Heap snapshots, detached DOM nodes, memory leaks         |
| Lighthouse / PageSpeed Insights     | LCP, INP, CLS, TTFB, bundle size                         |
| React DevTools → Profiler           | Component render counts, render duration, wasted renders |
| `@next/bundle-analyzer`             | Webpack/Turbopack chunk composition, module sizes        |
| `why-did-you-render`                | Detects avoidable React re-renders in development        |
| WebPageTest                         | Real-device network waterfall, TTFB from edge            |

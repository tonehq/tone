# <Feature Name> — Requirements

<!--
GLOBAL STANDARD for a feature PRD. One folder per feature: prd/<feature-name>/requirements.md (kebab-case).
This file is AUTHORED BY THE USER — plan-mode scaffolds this empty shape at intake and READS it as the
plan's source of truth; it never fills or overwrites it (except an approved, task-driven change).
- Keep the section order and numbering. Number requirements (R1, R2, …) so acceptance criteria can cite them.
- Sections 3–6 are for UI / frontend features — DELETE them for pure backend / infra features.
- Fill section 7's "APIs & data model" for any backend / contract / DB change.
-->

<One-paragraph summary: what this feature is, who it's for, and the intent. Describe the current/target behavior in plain language.>

## 1. Overview

- **Route(s) / entry points:** `<path or API endpoint>` (framework / route group, if relevant)
- **Goal:** <the outcome this feature delivers and why>
- **Scope:** <which layers are touched — frontend / backend / DB / infra. State explicitly what is NOT changing.>
- **Shared / affected surfaces:** <any layout, component, endpoint, or contract reused elsewhere that this touches>

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `<path/to/file>` | <what it does for this feature> |
| … | … |

## 3. Layout & Structure   *(UI features — delete if not applicable)*

- <Page/screen composition, regions, and how they nest.>
- **Responsive:** <breakpoint behavior; what shows/hides at each size.>

## 4. Content & Copy   *(UI features — delete if not applicable)*

<Exact strings, grouped by region: headings, labels, placeholders, CTA text, empty/error/success messages, conditional copy.>

## 5. Theming & Colors   *(UI features — delete if not applicable)*

- **Token-driven:** <which design-system tokens are used; call out any intentional exceptions.>
- **Light & dark parity** · **Accessibility:** <contrast (WCAG AA), focus/hover visibility.>

## 6. Motion & Animation   *(UI features — delete if not applicable)*

- <Entrance/exit animations, easing, stagger, triggers, and cleanup for any looping motion.>

## 7. Behavior & Functionality

- **Validation:** <rules and where errors surface.>
- **Primary action(s):** <what happens on submit/click; success + failure paths; side effects.>
- **State & data:** <server state, client state, redirects, query params, storage rules.>
- **APIs & data model:** <endpoints + request/response shapes; DB schema / migrations; multi-tenancy / org-scoping / RBAC — or explicitly "none".>
- **Error handling:** <how API / runtime errors are surfaced.>

## 8. Non-Functional Requirements

- **Standards compliance:** <project code standards this must satisfy; lint / typecheck / tests pass.>
- **Performance:** <constraints and expectations.>
- **SSR / hydration safety:** <if applicable.>
- **Security:** <auth, RBAC / org-scoping, tokens, redirects, data handling.>
- **Observability:** <logs / metrics / errors to add, if any.>

## 9. Acceptance Criteria

- [ ] <Testable, specific outcome — reference R1 / R2 / …>
- [ ] <Primary flow works end-to-end; error / edge paths handled>
- [ ] <UI: copy matches §4; theming correct in light & dark with AA contrast; responsive layouts intact — delete if non-UI>
- [ ] <Tests added; lint + typecheck pass with no new violations>

## 10. Out of Scope

- <Explicitly excluded work — related features, flows, or layers not touched here.>

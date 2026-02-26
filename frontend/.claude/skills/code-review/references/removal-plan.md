# Removal and Iteration Plan

<!-- Global Frontend Standard — React + Next.js -->
<!-- Read the Detection and Validation rules before filling any section -->

---

## Detection Objectives

Detect and classify candidates under one of these categories:

| #   | Category                       | Signals                                                                           |
| --- | ------------------------------ | --------------------------------------------------------------------------------- |
| 1   | **Dead code**                  | Unused exports, unreachable branches, zero call-site functions, orphan components |
| 2   | **Stale feature flags**        | Always `true`, always `false`, no environment variance, no expiration metadata    |
| 3   | **Deprecated API / component** | Old version coexisting with new, JSDoc `@deprecated` present                      |
| 4   | **Duplicate logic**            | Same utility repeated in 2+ files, repeated transformation logic                  |
| 5   | **Commented-out code**         | Large disabled blocks, disabled components                                        |
| 6   | **Unused dependency**          | Package removed from imports and from all usage                                   |

---

## Next.js Safety Validation

Before marking anything 🔴 **Safe to Remove Now**, verify it is NOT:

- Part of filesystem routing (`app/` or `pages/` route structure)
- Used in `layout.tsx`, `page.tsx`, `loading.tsx`, or `error.tsx`
- Referenced in `middleware.ts`
- Referenced in `getServerSideProps`, `getStaticProps`, or `generateMetadata`
- Dynamically imported via `next/dynamic`
- Used in API routes
- Wrapped in root providers
- Referenced inside MDX

If uncertainty exists → classify as 🟡 **Defer Removal**
If high runtime risk → classify as ⚠️ **Do Not Remove**

---

## Dynamic Access Safety

If the identifier may be consumed via any of the following, mark as ⚠️ **Do Not Remove**:

- `obj[key]` — string-based dynamic access
- String constants matched at runtime
- Analytics or telemetry event names
- Feature flag keys read from a remote config service
- `data-testid` attributes (silently breaks E2E tests)
- CMS-injected or third-party class names

---

## 1. Safe to Remove Now 🔴

Zero live consumers, not referenced dynamically, passes Next.js safety validation.

### [SHORT NAME]

- **Location**: `path/to/file.tsx:line`
- **Category**: Dead code | Stale flag | Deprecated API | Unused dep | Duplicate logic | Commented-out code
- **Evidence**: Clear explanation — e.g. "No references found via search; flag hardcoded `false` since YYYY-MM-DD"
- **Runtime risk**: None — validated against Next.js routing and dynamic access rules
- **Deletion steps**:
  1. Remove the code / file / package
  2. Remove associated types and interfaces
  3. Remove related tests, fixtures, and mocks
  4. Run verification checklist (see below)

> If none found: **"No immediate safe removals detected."**

---

## 2. Defer Removal 🟡

Active consumers exist, or removal requires a migration path first.

### [SHORT NAME]

- **Location**: `path/to/file.tsx:line`
- **Category**: Deprecated API | Duplicate logic | Other
- **Why defer**: Active consumers / needs migration / cross-team dependency
- **Breaking changes**: List API or type contract changes that consumers will feel
- **Deprecation step**: Add `@deprecated` JSDoc + `console.warn` in dev only
- **Migration plan**:
  1. Identify all consumers (search / IDE find-usages)
  2. Migrate each consumer to the replacement
  3. Open a tracking issue with a target sprint
  4. Remove once consumers == 0
- **Target sprint / issue**: JIRA-XXX or GitHub #XXX

> If none found: **"No deferred removals."**

---

## 3. Do Not Remove ⚠️

Items with hidden runtime consumers — flag to prevent accidental deletion.

| Item                | Reason                                                    |
| ------------------- | --------------------------------------------------------- |
| `identifier`        | Consumed via `obj[key]` dynamic access                    |
| `EVENT_NAME`        | Referenced as analytics string constant in data warehouse |
| `flag-key`          | Read from remote feature flag service                     |
| `data-testid="..."` | Tied to E2E test selectors                                |
| `.class-name`       | Injected by CMS or third-party script                     |

> If none found: **"No hidden-consumer risks identified."**

---

## 4. Unused Dependency Removal

### [PACKAGE NAME]

- **Package**: `package-name@version`
- **Evidence**: No `import` or `require` in `src/`; not referenced anywhere in the repo
- **Config check**: Not listed in `babel.config.js`, `.eslintrc`, `postcss.config.js`, or bundler config
- **Removal steps**:
  1. `npm uninstall package-name` / `yarn remove package-name` / `pnpm remove package-name`
  2. Search for config-file-only references and remove them
  3. Run build to confirm no implicit transitive dependency

> If none found: **"No unused dependencies detected."**

---

## Pre-Removal Checklist

Complete every item before merging a removal PR.

### Discovery

- [ ] Searched entire codebase for the identifier (not just the file path)
- [ ] Checked for string-based / dynamic access (`obj['key']`, template literals, `require()`)
- [ ] Confirmed no active usage via analytics dashboard or feature-flag service
- [ ] Checked config files — bundler, linter, test runner

### Safety

- [ ] Removal is in its own focused PR — not bundled with feature work
- [ ] Associated types and interfaces are also removed
- [ ] Related tests, fixtures, and mocks are removed or updated
- [ ] No parallel open PR adds a new consumer of this code

### Verification

- [ ] Linter passes (`eslint` / `biome` / project linter)
- [ ] Type-check passes (`tsc --noEmit`)
- [ ] Build passes (`next build` / project build command)
- [ ] Tests pass (if test suite exists)

> **When reviewing a diff:** mark all checklist items as `[ ] Requires manual verification`

---

## Rollback Plan

If a removal causes an unexpected production failure:

1. **Revert the PR immediately** — do not patch forward under pressure
2. Identify the hidden consumer missed during discovery
3. Add it to the **Do Not Remove** section above with evidence
4. Re-open a tracking issue with the additional context before attempting removal again

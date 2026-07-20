# Code Review Rules

Globally-standard, reusable code review guidelines for this repo. Applies to every PR.

Two rulebooks, one shared philosophy:

- **[Frontend — Next.js / React / TypeScript](./frontend-nextjs-typescript.md)**
- **[Backend — Python / FastAPI / SQLAlchemy](./backend-python-fastapi.md)**

---

## Why these rules exist

Reviews are not a taste debate. Their job is to catch the classes of defects that
compilers, linters, and unit tests do **not** catch — broken invariants, security holes,
performance cliffs, leaky abstractions, and code that the next engineer can't safely change.
Style is already enforced by ESLint + Prettier (FE) and Ruff + formatter (BE); **do not
spend review cycles on style a tool can fix.**

## How to review (the loop)

1. **Read the PR description first.** No description, no context → ask for one. A reviewer
   should understand *what problem* and *why this approach* before reading a single line.
2. **Review the diff, then the surrounding code.** A diff can be locally correct and globally
   wrong. Open the files it touches and ask what invariants it might break.
3. **Categorize every comment** with a severity prefix so the author knows what blocks merge:
   - `[blocker]` — must fix before merge (bug, security, data loss, broken contract).
   - `[should]` — strong recommendation; fix or justify why not.
   - `[nit]` — optional polish; author's discretion.
   - `[question]` — you don't understand something yet; not necessarily a change.
   - `[praise]` — call out genuinely good work. Reviews are also teaching.
4. **Prefer suggestions over commands.** "What happens if `items` is empty here?" teaches more
   than "add a guard." Suggest concrete code when it's faster than prose.
5. **Approve when it's better than what's on `dev`, not when it's perfect.** Perfection blocks
   shipping. File `[nit]`s and move on.

## Universal review checklist (both stacks)

**Correctness**
- [ ] Does it actually solve the stated problem? Re-read the ticket/PR description.
- [ ] Edge cases: empty list, null/None, zero, negative, very large, unicode, timezone.
- [ ] Error paths handled — not just the happy path. What does the user/caller see on failure?
- [ ] No off-by-one, no swapped arguments, no inverted boolean.
- [ ] Concurrency: shared state, race conditions, non-idempotent retries.

**Security** (see stack-specific files for detail)
- [ ] No secrets, tokens, API keys, or PII in code, logs, or error messages.
- [ ] All external input validated at the boundary before use.
- [ ] AuthN + AuthZ enforced — the caller is who they claim **and** allowed to do this.
- [ ] No injection surface (SQL, shell, template, XSS, SSRF).

**Design & reuse** (the "reusable as much as possible" bar)
- [ ] Does this duplicate something that already exists? Search before adding.
- [ ] Is the abstraction at the right layer? (UI ≠ business logic ≠ data access.)
- [ ] Single responsibility — a function/component/service does one thing.
- [ ] Public surface is minimal — export only what callers need.
- [ ] Names say what, not how; no misleading names.
- [ ] No magic constants or pure helper functions inlined in a component/module — they
      live in a dedicated constants file and a helper/util file (see DRY doctrine).

**Tests**
- [ ] New behavior has tests. Bug fixes have a regression test that fails without the fix.
- [ ] Tests assert behavior, not implementation details.
- [ ] Edge cases and error paths are covered, not only the happy path.

**Observability & ops**
- [ ] Failures are logged with enough context to debug (ids, not secrets).
- [ ] Every error-handling `except` captures a **full traceback** (BE: `logger.exception`; expected
      control-flow → `logger.debug`) — no message-only error logs, no silent swallow, `CancelledError`
      never caught-and-dropped.
- [ ] No noisy logs in hot paths; no `console.log` / `print` left behind.
- [ ] Migrations, feature flags, and config changes are called out in the PR.

**Docs & hygiene**
- [ ] Non-obvious decisions have a comment explaining **why** (not what).
- [ ] No dead code, commented-out blocks, or stray TODOs without an owner/issue.
- [ ] Public API / schema / env-var changes are documented.

## The DRY / reuse doctrine

Reuse is a review priority in this repo, but **premature abstraction is a defect too.**

- **Single source of truth (blocker-class).** A given piece of functionality has exactly
  one implementation, and every call site — another router, a worker, a CLI, a test, a
  second page — goes through it. If a PR re-implements or copy-pastes behavior that an
  existing service/helper/hook already provides, that's a `[blocker]`/`[should]`: the fix
  is "call the shared function," not "duplicate it here." Before approving new logic, ask
  "does this already exist, and will it be needed elsewhere?" — if yes, it belongs in a
  shared service (`BaseService`) / `core/services/common` / `core/utils` (BE) or
  `@/components/shared` / `@/hooks` / `@/lib` / `@/utils` / `@/services` (FE).
- **Logic goes through the service layer, always.** Routers/controllers and components stay
  thin; domain logic lives in a service so it is reusable and testable from anywhere. Flag
  any business logic, raw query, or multi-model rule that sits in a router or component.
- **Rule of three.** Two occurrences → leave it. Three → extract a shared helper/component/service.
- **Extract by responsibility, not by shape.** Two blocks that *look* similar but change for
  *different reasons* should stay separate. Coupling them creates a helper with five boolean
  flags — worse than the duplication.
- **Put shared code where it belongs:**
  - FE: shared UI → `@/components/shared`; shared logic → `@/hooks`, `@/lib`, `@/utils`;
    shared API → `@/services`; shared types → `@/types`.
  - BE: shared logic → a service extending `BaseService`; shared helpers → `core/utils`;
    shared schemas → Pydantic models reused across routers.
- **A helper with more than ~3 config flags is a smell.** Split it.
- **Don't inline constants or pure helper functions in a component.** Magic strings/numbers
  and stateless helpers (label maps, formatters, sentinel values, `countLabel`-style
  utilities) belong in a **dedicated constants file** and a **helper/util file** — not at the
  top or bottom of the component that first used them. Co-locate feature-specific ones beside
  the feature (e.g. `readinessConstants.ts` / `readinessHelpers.ts`); promote to `@/utils`
  (FE) or `core/utils` (BE) once a second feature needs them (rule of three). This keeps
  components JSX-only and the logic reusable + unit-testable.

## Author's pre-flight (run before requesting review)

- FE: `npm run lint && npm run build` pass; `npm run format` applied.
- BE: `ruff check . && pytest` pass; type checks clean.
- Self-review your own diff first — you'll catch half the reviewer's comments.
- Keep PRs small (< ~400 lines of real change). Large PRs get shallow reviews.
- Branch + session naming follows the team workflow (`feature/staging/<name>`, PLAN/IMPLEMENT).

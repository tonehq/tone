# E2E scenarios — index

This folder catalogues every Playwright e2e scenario that lives under
`frontend/e2e/dashboard/`. Each suite has its own companion doc, listed
below with its scenario-ID prefixes, what's covered, and what's deferred.

> All docs in this folder are tracked via `git add -f` because the
> `e2e/docs/` directory is project-gitignored (see `.gitignore:151`).

## Conventions

- **Real backend** — every suite drives the real backend through the UI
  via the worker-fixture login (`frontend/e2e/helpers/auth.ts`). No
  `page.route` mocks anywhere.
- **`__e2e__` prefix** — every fixture row created during a run is
  name-prefixed with `__e2e__` so a sweep can pick up orphans from
  aborted runs.
- **`try/finally` cleanup** — every test that creates a row deletes it
  in the same test body, even on assertion failure.
- **Comprehensive `*-FULL` flow** — each suite ends with a single test
  that walks the user's full lifecycle (create → mutate every field →
  read back → delete) and asserts persistence after a reload.
- **Scenario IDs** — `{TWO_LETTERS}-{NUMBER}` per topic (e.g. `MPC-001`
  for "Model Providers — Create — scenario 001"). The `*-FULL` suffix
  is reserved for the comprehensive flow.

## Suite catalogue

| Suite | Spec file | Doc | Scenario prefixes | Active | Deferred |
|---|---|---|---|---|---|
| Agents — list | `agents.spec.ts` | (covered by AC / AE docs) | `AL-` | varies | — |
| Agents — create (inbound) | `agents-create-inbound.spec.ts` | [agents-create.md](agents-create.md) | `AC-` + `AC-FULL` | 17 | 13 (`test.fixme`) |
| Agents — create (outbound) | `agents-create-outbound.spec.ts` | (shares agents-create.md) | `ACO-` | 3 | — |
| Agents — edit | `agents-edit.spec.ts` | [agents-edit.md](agents-edit.md) | `AE-` + `AE-FULL` | 12 | 10 (`test.fixme`) |
| Tools — list | `tools.spec.ts` | (mock-based, no doc) | inline names | — | — |
| Tools — create | `tools-create.spec.ts` | [tools-create.md](tools-create.md) | `TC-` + `TC-FULL` | 17 | 3 (`test.fixme`) |
| Tools — edit | `tools-edit.spec.ts` | [tools-edit.md](tools-edit.md) | `TE-` + `TE-FULL` | 9 | 6 (`test.fixme`) |
| Members + Invitations | `members.spec.ts` | [members.md](members.md) | `ML-` / `MI-` / `MR-` / `MD-` / `INV-` / `MM-FULL` | 16 | 3 (`test.skip` / `test.fixme`) |
| Organizations | `organizations.spec.ts` | [organizations.md](organizations.md) | `OL-` / `OC-` / `OE-` / `OD-` / `OS-` / `OG-FULL` | 14 | 3 (`test.skip` / `test.fixme`) |
| Model Providers — list | `model-providers.spec.ts` | [model-providers.md](model-providers.md) | `MPL-` / `MPC-` / `MPP-FULL` | 9 | 4 (`test.fixme`) |
| Model Providers — detail (Keys + Models tabs) | `model-providers-detail.spec.ts` | [model-providers-detail.md](model-providers-detail.md) | `AKL-` / `AKC-` / `AKE-` / `AKD-` / `AKK-FULL` + `MDL-` / `MDC-` / `MDE-` / `MDD-` / `MDM-FULL` | 17 | 4 (`test.fixme` / `test.skip`) |
| Auth — login | `e2e/auth/login.spec.ts` | (separate, mock-based) | inline | — | — |
| Auth — signup | `e2e/auth/signup.spec.ts` | (separate, mock-based) | inline | — | — |
| Home | `e2e/dashboard/home.spec.ts` | [home.md](home.md) | inline | — | — |

**Total dashboard scenarios across the new real-backend suites: ≈ 130
active + 42 deferred.**

## Scenario-ID prefix reference

Prefixes are 2-3 letters chosen to be mnemonic without colliding:

| Prefix | Meaning |
|---|---|
| `AL-` | Agents — List |
| `AC-` | Agents — Create |
| `AE-` | Agents — Edit |
| `ACO-` | Agents — Create Outbound |
| `TC-` | Tools — Create |
| `TE-` | Tools — Edit |
| `ML-` | Members — List |
| `MI-` | Members — Invite modal |
| `MR-` | Members — Role change |
| `MD-` | Members — Delete |
| `INV-` | Members — Invitation row actions (resend / cancel) |
| `MM-` | Members — Comprehensive flow only |
| `OL-` | Organizations — List |
| `OC-` | Organizations — Create modal |
| `OE-` | Organizations — Edit modal |
| `OD-` | Organizations — Delete modal |
| `OS-` | Organizations — Sidebar switch |
| `OG-` | Organizations — comprehensive flow only |
| `MPL-` | Model Providers — List |
| `MPC-` | Model Providers — Create drawer |
| `MPE-` | Model Providers — Edit drawer |
| `MPD-` | Model Providers — Delete (card) |
| `MPP-` | Model Providers — Comprehensive flow only |
| `AKL-` | API Keys — List (detail page Keys tab) |
| `AKC-` | API Keys — Create |
| `AKE-` | API Keys — Edit |
| `AKD-` | API Keys — Delete |
| `AKK-` | API Keys — Comprehensive flow only |
| `MDL-` | Provider Models — List (detail page Models tab) |
| `MDC-` | Provider Models — Create |
| `MDE-` | Provider Models — Edit |
| `MDD-` | Provider Models — Delete |
| `MDM-` | Provider Models — Comprehensive flow only |

When adding a new suite, pick a 2-letter prefix that doesn't collide
with anything above and document it in this table.

## Running the suites

```bash
# Prerequisites
cd frontend && yarn install && yarn playwright install chromium

# Each suite has its own script in package.json:
yarn test:e2e:agents          # AL-/AC-/AE-/ACO-
yarn test:e2e:tools           # TC-/TE-
yarn test:e2e:members         # ML-/MI-/MR-/MD-/INV-/MM-
yarn test:e2e:organizations   # OL-/OC-/OE-/OD-/OS-/OG-
yarn test:e2e:providers       # MPL-/MPC-/AKL-/AKC-/AKE-/AKD-/AKK-/MDL-/MDC-/MDE-/MDD-/MDM-
```

All scripts run on the `chromium` project with `--workers=1` and the
`list` reporter so failures are immediately readable. The dev server
(`yarn dev`) and backend (`python main.py` from the repo root) must be
running before invoking.

## Shared helpers

Every suite is built on shared fixtures under `frontend/e2e/helpers/`.
Use these directly when adding new specs:

| Helper file | Used by |
|---|---|
| [`auth.ts`](../helpers/auth.ts) | shared worker-fixture login (every suite imports `test` from here) |
| [`agentFixtures.ts`](../helpers/agentFixtures.ts) | Agents suite — also exports `pickFirstSelectOption` which the other suites re-use |
| [`toolFixtures.ts`](../helpers/toolFixtures.ts) | Tools suite — also exports `pickSelectOptionByLabel` which the Members + Providers suites re-use |
| [`memberFixtures.ts`](../helpers/memberFixtures.ts) | Members + Invitations |
| [`organizationFixtures.ts`](../helpers/organizationFixtures.ts) | Organizations + org switch helper |
| [`serviceProviderFixtures.ts`](../helpers/serviceProviderFixtures.ts) | Model Providers + API Keys + Models |

Reuse patterns from the most recent suite (`serviceProviderFixtures.ts`)
when adding a new feature — it includes the hydration-wait, response-
interception, and cleanup patterns that the earlier helpers grew over
time.

## Safety constraints (every suite respects these)

The test user (`kishok.k@productfusion.co`, owner of "My Space") shares
the dev backend. Every suite is written to:

- **Never** delete or rename `My Space` (the worker's primary org).
- **Never** mark a test resource as `is_default=true` — the user's real
  agent saves pick up defaults and would be affected.
- **Never** touch real (non-`__e2e__`) rows.
- **Always** clean up in `try/finally`.

The orgs/providers docs go into the specific edge cases each suite
hits (e.g. `OS-002` switching tenants is `test.fixme` because the
sidebar swap races with the JWT in cookies).

## Backend gaps surfaced during the work

Documented in detail in each suite's doc, summarised here:

| Suite | Gap | Suite scenario(s) blocked |
|---|---|---|
| Members | `Invite.to_dict()` omits the token, so no programmatic invite-accept | MR-002, MD-002, OD-001 |
| Organizations | `website_url` (FE) ↔ `Organization.website` (BE) mapping mismatch — doesn't round-trip on reload | OE-003 (asserts description only), OG-FULL (same) |
| Organizations | Sidebar switch is localStorage swap + reload with no `/auth/switch_organization` call, so the JWT stays on the old org_id | OS-002 (`test.fixme`) |
| Model Providers | List-page card aggregates by `(provider, service_type)` and only puts the key label in a tooltip title attribute | MPD-001/002 (`test.fixme`) |
| Model Providers | API-key secret is returned once on POST but the FE never re-displays it (no UI to assert the masking) | AKR-MASK deferred |
| Model Providers | `ProviderModel` has no `org_id` — the model catalog is global, so every test must `__e2e__`-prefix and clean up | mitigation, not a blocker |

## Adding a new suite

1. Pick a 2-letter prefix (see table above) and document it.
2. Create a `*Fixtures.ts` helper following the
   `serviceProviderFixtures.ts` shape (hydration waits, response
   interception, soft-cleanup helpers).
3. Create the spec file in `frontend/e2e/dashboard/` mirroring
   one of the existing suites — start with `members.spec.ts` for a
   single-page CRUD or `model-providers-detail.spec.ts` for tabbed flows.
4. Create the doc in `frontend/e2e/docs/` mirroring the structure of
   `model-providers.md`:
   - **User stories** → **Routes** → **Key files** → **API endpoints
     exercised** → **Scenarios table** → **Comprehensive flow field
     table** → **Coverage map** → **Deferred** → **Cleanup**.
5. Force-add the doc with `git add -f`.
6. Add a `test:e2e:{feature}` script to `frontend/package.json`.
7. Add a row to the suite-catalogue table at the top of this README.

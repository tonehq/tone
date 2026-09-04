---
name: create-model-provider
description: "Add an LLM, STT or TTS provider — or new models/voices for an existing one — to the Tone voice pipeline end to end. Analyses the repo first to work out what is already wired, asks what to add, collects the required fields and credential from the user, works on a fresh branch off dev, writes the service_factory branch if one is needed, adds the provider to the database, verifies, reviews its own diff against the repo rulebook and fixes what it finds, then opens a PR to dev. Use when the user says add a provider, add a model, wire up a new STT/TTS/LLM, onboard a vendor, names a provider to integrate, or asks to update or delete an existing provider or model."
---

# Create Model Provider

## Operating rules

1. **Hardcode nothing.** No vendor list, no endpoint list, no field list lives in this
   skill. Everything about the repo is derived by `analyze.py`; everything about the
   vendor comes from the user.
2. **Analyse before asking.** Run Step 0, then build the questions from what it found.
   Never present a fixed menu of vendors — the user may want one nobody has heard of.
3. **Never ask the user for API docs, and do not go looking for them.** Ask for the
   concrete values you need: the endpoint URL, the header the key goes in, the model ids.
   If the user does not have a catalogue endpoint, take the ids from them directly and
   move on.
4. **Branch first, PR at the end.** Never edit on `dev` or `main`. Step 1 cuts a fresh
   branch; Step 10 opens the PR into `dev`.
5. **Review your own work before the PR, and loop.** Step 9 reviews the diff against
   `docs/code-review/`, fixes what it finds, and reviews again. A single pass is not a
   review.
6. **Match the code that is already there.** Before writing anything, read the nearest
   existing example end to end — the neighbouring factory branch, the closest service
   class, a comparable seed entry — and follow its structure, naming, import order and
   error handling. The repo's conventions win over anything in this skill.
7. **Write no comments.** Not in the factory branch, not in a service class, not in the
   seed data. Name things so the code reads without them. The existing files are the
   standard to match.
8. **Never invent a value that fails silently** — a URL, a model id, a metadata field
   name. Ask. Every item in Gotchas below is a value that produces no error when wrong.

Four things must agree or the provider breaks silently:

| Layer | Where | Failure if wrong |
|---|---|---|
| Code | `core/services/pipeline/service_factory.py` | `build_*` returns `None` → no service |
| Data | `dev/dev-data.json` → DB | Invisible in the UI |
| Credential | `api_key_env` in `.env` | **Resolver returns no spec — the agent runs with the service missing** |
| Contract | metadata names vs Pipecat `InputParams` | Controls render and do nothing |

Run scripts from the repo root with the venv:
`venv/bin/python .claude/skills/create-model-provider/scripts/<name>.py`

---

## Step 0 — Analyse

```bash
venv/bin/python .../scripts/analyze.py                 # inventory + derived schema
venv/bin/python .../scripts/analyze.py --provider NAME # verdict for one
venv/bin/python .../scripts/analyze.py --json          # to drive your questions
```

This parses `dev-data.json` and `service_factory.py` and derives: the layers that exist,
every provider and its wiring state, the factory branches (including generic-fallback
keys parsed from source), and the entry schema — required keys, optional keys and valid
enum values — inferred from the entries already present.

**Use the derived schema as the source of truth for what to ask.** Do not use the field
lists in `reference/seed-schema.md` as a checklist; they are explanation, and the file
can go stale. `analyze.py` cannot.

Report the state, then skip whatever is already done:

| State | Work |
|---|---|
| Seeded + wired + key | Nothing. Offer models/voices instead |
| Branch, no seed row | Data only — skip Step 4 |
| Seed row, no branch | Code only — skip Step 5 |
| Neither | Full flow |

---

## Step 1 — Branch

Before editing anything. All work happens on a fresh branch off `dev` — never on `dev`,
never on `main`, never on whatever the user happens to have checked out.

```bash
git rev-parse --abbrev-ref HEAD                     # report the current branch
git fetch origin && git switch -c <branch> origin/dev
```

Name it for the work, kebab-case, matching the repo's existing style:
`add-<vendor>-<layer>-provider`, e.g. `add-sarvam-stt-provider`.

If the working tree is dirty, stop and show `git status` — do not stash or commit someone
else's changes. Ask whether to branch from the current state or have them clean it first.

---

## Step 2 — Ask what to add

**AskUserQuestion**, one question per call, options built from Step 0's output.

**a. What is this run?** Build the options from what the analysis found — e.g. "add a
provider that has a branch but no seed row" (list the actual orphans), "add models to an
existing provider" (list them), "add something new", **"update an existing provider or
model"**, **"delete one"**. Do not offer a state that does not exist in this repo right now.

For **update** or **delete**, skip Steps 3 and 4 and go to Step 7 — the identity, the
credential and the catalogue are already settled. For update, ask which fields change and
change only those. Everything else in the flow still applies: branch first, review, PR.

**b. Which vendor, and which layer(s)?** Free text for the name — never a menu.
`multiSelect` the layers; one vendor can serve several, and each is a separate entry and
a separate branch. Collect the slug too: **the factory keys off `provider.slug`**, which
seed derives from `name`, so a mismatch means the branch never fires.

**c. Integration path** — decides whether any code gets written:

- If the analysis shows a **generic fallback map** for this layer and the vendor's API is
  OpenAI-shaped → **no branch**; add the vendor to that map. Ask the user whether their
  API is OpenAI-compatible; do not assume.
- Otherwise → a dedicated branch.
- Layers with no fallback map always need a branch.

**d. Pipecat service class** — ask the user for the import path, then verify:

```bash
venv/bin/python .../scripts/inspect_pipecat.py <import.path.Class>
venv/bin/python .../scripts/inspect_pipecat.py --search <vendor>
```

Prints the constructor and `InputParams` fields — **that list is the contract** — and
flags classes that select the model through a side channel rather than `model=`.

**If no class exists, write one** — do not stop, and do not send the user to the
`tone-pipecat` fork. This repo already keeps custom service classes in
`core/services/pipeline/` (`parakeet_stt_service.py`, `granite_stt_service.py`,
`cosyvoice_tts_service.py`, `qwen_tts_service.py`,
`mistral_self_hosted_llm_service.py`). Follow `reference/writing-a-service-class.md`:
pick the base class from the transport, copy the structure of the closest existing file,
and implement the same surface it does. Then wire the branch to it in Step 5.

Ask the user for the wire details you cannot know — the protocol, the request and
response shape, the audio encoding. Do not guess a protocol; a wrong one fails at the
first audio frame.

---

## Step 3 — Credential

1. Step 0 reports whether `api_key_env` is set.
2. If not, ask the user for the value and append it to `.env`. Never print it back, never
   commit it, never put it in `dev-data.json`.
3. **A self-hosted or keyless provider still needs a placeholder value.**
   `_make_service_spec` (`service_resolver.py:136`) returns `None` when `api_key` is
   falsy, and `dev/seed_org.py` skips the `ApiKey` row when the env var is unset. The
   result is not an error — the agent resolves no spec for that layer and runs with the
   service missing.
4. Staging secrets come from Infisical, not `.env`. Do not touch them unless the user authorised it.

---

## Step 4 — Models and voices

Ask the user which of two routes applies. **Do not ask for documentation.**

**a. They have a catalogue endpoint.** Ask for the URL, the header the key goes in, and
any extra header (an API version, say). Then:

```bash
venv/bin/python .../scripts/fetch_catalog.py --url <URL> --env <ENV_VAR> \
    [--auth-header X-API-Key] [--auth-prefix ""] [--auth-query key] \
    [--header "Version: 2024-06-10"] [--json-path data] \
    [--id-field voice_id] [--label-field name] [--emit-seed <layer> --name <slug>]
```

The script knows nothing about any vendor — it sends what you tell it and auto-detects
the list and id fields, printing what it guessed so you can confirm. `--raw` dumps the
response when the shape is unfamiliar. On 401/403 or 404 it says which input to
re-confirm with the user rather than retrying blind.

**b. They do not.** Collect model ids — and voice ids for TTS — directly from the user.
That is a normal outcome, not a failure.

Either way, **confirm the final selection**. A catalogue often returns far more than is
worth seeding; ask which to include rather than seeding everything.

---

## Step 5 — Code

Two possible pieces of code here.

**A service class**, if Step 2d found none — `reference/writing-a-service-class.md`.

**The factory branch**, if Step 2c called for one — `reference/factory-patterns.md`.
Insert alongside the existing branches in the same `build_*`, matching surrounding style.
Logic stays in the factory.

Both follow operating rules 6 and 7: match the neighbouring code, and add no comments.
The templates in the reference files carry explanatory comments so they can be read —
strip them when you paste.

## Step 6 — Data

**Both are required. This is not a choice, and the API is not optional.**

The provider must land in the **staging database via the API**, and the same entry must
be recorded in `dev/dev-data.json` so a fresh environment gets it too. A run that only
edits the seed file has not added the provider — the seed file is a recipe, not the
database. Do not end a run by telling the user to go run `seed.py` themselves.

- **API (writes to a running DB) — prefer a local server, fall back to staging.**
  If something is listening on `localhost:8000` use that; a dev run should not write to a
  shared environment by accident. Otherwise target staging at
  `https://staging-api.trytone.ai/api/v1`, reading the domain from
  `build/kubernetes/envs/staging.env` → `API_DOMAIN` rather than pasting it, so a renamed
  environment cannot silently receive writes.

  ```bash
  curl -sf -o /dev/null --max-time 2 http://localhost:8000/health \
      && BASE=http://localhost:8000/api/v1 \
      || BASE=https://$(grep -m1 '^API_DOMAIN=' build/kubernetes/envs/staging.env | cut -d= -f2)/api/v1
  echo "writing to $BASE"
  ```

  **Say which base you resolved before the first write**, so the user can stop you if it
  is not the environment they meant.

  ```bash
  TOKEN=...                                   # see "Authenticating" below
  curl -sS -X POST "$BASE/services/providers/create_provider" \
       -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @provider.json
  curl -sS -X POST "$BASE/services/providers/<provider_id>/models/create" \
       -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @model.json
  curl -sS -X POST "$BASE/services" \
       -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @key.json
  ```

  **Authenticating.** These routes are behind `require_admin_or_owner`, so the token must
  belong to an admin or owner of the org. Log in with the staging account whose
  credentials live in `.env` as `TONE_STAGING_EMAIL` / `TONE_STAGING_PASSWORD`
  (`parandhama.reddy@trytone.ai`) — read them from there, never inline them:

  ```bash
  BASE=https://staging-api.trytone.ai/api/v1
  EMAIL=$(grep '^TONE_STAGING_EMAIL=' .env | cut -d= -f2-)
  PASSWORD=$(grep '^TONE_STAGING_PASSWORD=' .env | cut -d= -f2-)
  TOKEN=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
      -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
  ```

  Confirm the response field name against `core/api/v1/auth.py` before relying on
  `access_token`. If either variable is missing, ask the user rather than guessing. Never
  echo the password or the token back, never pass them on a command line that gets logged,
  and never write them into a tracked file — `.env` is gitignored, `SKILL.md` is not.

  **Then attach the provider key.** `POST $BASE/services` creates the `ApiKey` row that
  binds the provider, the org and the credential. Until that row exists the resolver
  returns no spec and the agent runs with the service missing, however correct the
  provider and model rows are. Verify it landed with
  `POST $BASE/services/providers/{provider_id}/keys`.

  **Staging is shared.** Print the exact payload and the target URL and get the user's
  confirmation before the first POST. Writes here are visible to everyone using the
  environment, and there is no undo beyond the delete endpoints.
- **`dev/dev-data.json`, committed in the same PR.** So the next fresh environment gets
  the provider. `seed.py` only applies it to an empty DB — it skips existing rows rather
  than updating them, so it is never the way a running environment gets the change.

> **Blocking gap — fix it in this run, do not route around it.** `create_provider_model`
> (`model_provider_service.py:1005`) constructs `Model(...)` with name, display_name,
> kind, description, base_url and is_active — it does **not** accept `meta_data` or
> `meta_data_schema`, and neither does `update_provider_model`. `meta_data` is where
> `{"model": "<id>"}` lives, so a model created purely through the API reaches the vendor
> with no model id.
>
> Verify the gap still exists, and if it does, **add `meta_data` and `meta_data_schema` to
> both service methods as part of this change** — it is a few lines in the service layer
> where the repo's own rules say the logic belongs, and it is a real defect for anyone
> adding a model through the UI or API, not just for this skill. Falling back to the seed
> path instead leaves the running environment without the provider, which is the failure
> this step exists to prevent. Flag it to the user before making the change, since it
> widens the diff beyond the vendor they asked for.
>
> Related: `CreateModelProviderRequest.meta_data_schema` is typed `Dict[str, Any]` while
> the seed format is a list — confirm which is correct before sending either.

For the file path, add the entry to the bucket `analyze.py` named, using the keys it
derived. Either way, validate before finishing:

```bash
venv/bin/python .../scripts/validate_provider.py <name> --service <pipecat.class.Path>
```

Rules are derived from the existing entries, so a novel enum value or a missing key that
every other provider has gets flagged. `--service` adds the check that matters most:
metadata names against the real `InputParams`.

## Step 7 — Update and delete

Same branch, review and PR discipline as a create. Routes (all under
`$BASE = https://staging-api.trytone.ai/api/v1`, all `require_admin_or_owner`):

| Intent | Route |
|---|---|
| Update a provider | `PUT $BASE/services/providers/update_provider/{provider_id}` |
| Update a model | `PATCH $BASE/services/providers/{provider_id}/models/{model_id}` |
| Update an attached key | `PATCH $BASE/services/{service_id}` |
| Delete a model | `DELETE $BASE/services/providers/{provider_id}/models/{model_id}` |
| Delete a provider | `DELETE $BASE/services/providers/delete_provider/{provider_id}` |
| Detach a provider's keys | `DELETE $BASE/services/providers/{provider_id}` |
| Delete an attached key | `DELETE $BASE/services/{service_id}` |

**Two DELETE routes differ by one path segment and do very different things.**
`/providers/delete_provider/{id}` removes the provider. `/providers/{id}` removes that
provider's `ApiKey` rows and leaves the provider standing. Read the path back to the user
before sending it.

**The delete guards are uneven — this is the part to be careful about.**

- `delete_provider` **blocks with 409** when any organisation still has an API key
  attached. Safe by default.
- `delete_provider_model` has **no such guard**. It is a hard `db.delete(record)`, and
  nothing checks whether an agent currently references that model. Deleting a model in use
  breaks those agents at their next call, with no warning at delete time.

So before deleting a model: confirm with the user that nothing uses it, and prefer
`is_active: false` via `PATCH` over deletion whenever the goal is "stop offering this".
Deactivating is reversible; deleting is not.

Before any destructive call, show the user the exact URL, the record it resolves to
(`GET $BASE/services/providers/get_provider/{id}` first), and what it will remove. Get
explicit confirmation. On a shared staging environment, do not batch deletes — one at a
time, each confirmed.

**Mirror the change in `dev/dev-data.json`.** An API update or delete changes the running
DB only; the seed file still carries the old shape and will reintroduce it in the next
fresh environment. Update or remove the entry there too, in the same PR.

## Step 8 — Verify

```bash
python dev/seed.py
venv/bin/python .../scripts/analyze.py --provider <name>
```

Must now report seeded + wired + key set. Then have the user place a **real test call** —
a provider can pass every check here and fail on the first request if a URL or model id
is wrong.

Against staging, re-check through the API (`POST $BASE/services/providers/list_providers`)
rather than `analyze.py`, which only ever reads local files.
`seed.py` is idempotent and skips existing rows, so editing `dev-data.json` does not
update a row already in the DB — say so rather than assuming a re-seed took effect.

---

## Step 9 — Review, and fix what it finds

Do not open a PR on unreviewed work. Review against the repo's own rulebook, then act on
the result — this is a loop, not a checkbox.

1. **Read the rulebook** — `docs/code-review/README.md` for the shared philosophy and
   severity labels, plus the stack file that matches what you touched
   (`backend-python-fastapi.md` for the factory and services).
2. **Review the diff.** Use the `/code-review` skill if available; otherwise review
   `git diff origin/dev...HEAD` yourself against the checklist. Pay particular attention
   to the always-check blockers: logic in the right layer, every query org-scoped, no
   raw SQL, secrets never logged, every `except` logging a full traceback.
3. **Re-run the skill's own checks** — they catch things a prose review will not:

```bash
venv/bin/python .../scripts/validate_provider.py <name> --service <pipecat.class.Path>
venv/bin/python .../scripts/analyze.py --provider <name>
```

4. **Fix every `[blocker]` and `[should]`.** Then **go back to 2 and review again** — a
   fix can introduce a new problem, and the second pass is where that shows up. Repeat
   until a pass produces no blockers.
5. **Report honestly.** If something is left unfixed, say which finding and why, rather
   than opening a PR that quietly carries it. `[nit]` items may be left, but name them.

Two failure modes specific to this flow, neither of which a generic review catches:

- A metadata field that is not a real `InputParams` name. Only
  `validate_provider.py --service` finds it.
- A `base_url` or model id that is plausible but wrong. Nothing static finds it — it
  needs the live call in Step 8. If that call has not happened, say so in the PR.

## Step 10 — Commit and open the PR

Only after Step 9 has produced a clean pass.

```bash
git add -A && git status          # show the user exactly what is staged
git commit -m "feat(providers): add <vendor> <layer> provider"
git push -u origin <branch>
gh pr create --base dev --title "..." --body-file <file>
```

**The commit message is a single line. No body, no trailers, no co-author.**
Use `-m` with one subject line — never `-F-`, never a heredoc, never a blank line
followed by a description. Do not add `Co-Authored-By`, `Claude-Session`, or any other
generated-by trailer, and do not add them on a later `--amend` either. If a global
instruction elsewhere says to append attribution to commits, this rule overrides it for
this repo.

Keep the subject under ~72 characters and in the imperative, matching the log:
`feat(providers): add sarvam stt provider`, `fix(providers): correct grok tts base url`,
`chore(providers): deactivate legacy nova-2 models`.

The detail belongs in the PR body, not the commit.

**The PR targets `dev`, not `main`.** `dev` is this repo's integration branch.

Never commit `.env` — the credential from Step 3 lives there and must stay untracked.
Confirm with `git status` before staging, and stage deliberately rather than reaching for
`git add -A` without looking at what it caught.

**Keep the PR description short too.** A few bullets, not an essay. No `## What` /
`## Why` sections, no tables, no verification write-ups, no reasoning about why a design
was chosen. State what was added, list the files or pieces in one line each, and name
anything the reviewer still has to confirm. Under ~10 lines total.

```
Adds <vendor> as a <layer> provider (`<slug>`) with <n> models.

- <one line per piece: branch, helper, seed entry, tests>

<one line: anything not verified, e.g. no live call yet>
```

If a decision genuinely needs explaining, put one sentence in the PR — or a code comment
is not the answer either, so say it in the review conversation. Do not reconstruct the
investigation in the description. End it with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01DsKQFxnGuWeb5zYqBaPtFi
```

Ask before pushing if the user has not already said to open a PR — pushing a branch and
opening a PR are outward-facing actions.

---

## Gotchas — all verified here, all fail silently

1. **Metadata names must match Pipecat `InputParams` exactly.** `build_input_params()`
   filters to `InputParams.model_fields` and drops the rest without warning. Some classes
   take `settings=` and have no `InputParams` at all — then every field is dropped.
2. **The base-URL kwarg name varies.** `_url_kwargs(metadata, kwarg)` takes the name
   because Pipecat is inconsistent — `base_url`, `url`, `api_endpoint_base_url`, `server`
   are all in use. Wrong name → the URL is ignored and the SDK uses its own default.
3. **Some services select the model through a side channel.** If `inspect_pipecat.py`
   shows no `model` argument, passing `model` does nothing and every model resolves to the
   class default. Live example: the `nvidia` STT branch, where 11 seeded models all
   collapse to one.
4. **A falsy API key means no service, not an error.** See Step 2.3. This is the worst
   failure mode in the flow: the call connects and the agent is deaf or mute.
5. **The factory keys off `provider.slug`**, not the display name. Seed derives it from
   `name`; keep them consistent with the branch key.
6. **Seed dedupes providers by name across buckets.** A vendor in two layers gets one
   `ModelProvider` row and only the first bucket's description survives.
7. **A default URL in the code is a guess about deployment.** Self-hosted branches fall
   back to a hardcoded cluster DNS name that may not match the deployed Service. Seed an
   explicit `base_url` on the model row; confirm the value with the user.
8. **TTS HTTP providers create their `aiohttp` session inside their own branch**, right
   before construction. A session created earlier leaks when a later import fails.
9. **`default` on a metadata field is a UI hint** — the factory does not apply it. If the
   service needs a value, set it in the branch.
10. **`seed.py` skips existing rows rather than updating them.**

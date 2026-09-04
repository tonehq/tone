---
name: test-agent
description: "Provision and drive three otherwise-identical voice agents, one per pipeline layer, so an STT, LLM or TTS swap can be attributed to that layer alone. Creates the agents from a single cloned baseline, swaps one layer on one agent, shows the current stack, and tears them down. Use when the user wants to A/B a provider, compare STT/LLM/TTS options on real calls, set up swap-test agents, or asks to change the model on a test agent."
---

# Test Agent

Three agents, identical except the layer under test:

| Agent | Vary | Config field |
|---|---|---|
| `swap-stt` | speech to text | `stt_settings` |
| `swap-llm` | language model | `llm_settings` |
| `swap-tts` | speech | **`voice_settings`** |

TTS lives in `voice_settings`, not `tts_settings` — the column does not exist.

**Why three agents rather than one you keep editing:** a single agent gives you no
control. Change its STT and something else drifts — a re-published config, a different
prompt version — and the call difference is unattributable. Here the three are created
by **cloning one baseline**, so they are identical by construction; swap one layer on one
agent and every other variable is held.

## Operating rules

1. **Hardcode nothing.** Providers and models come from the target environment's API at
   run time via `catalogue`. Never present a fixed vendor list.
2. **Ask for the baseline; do not choose it.** Which provider and model each layer starts
   on is the user's call. Run `catalogue`, show what the environment actually has, ask.
3. **Never invent a provider slug or model name.** Both are validated against the
   catalogue; a wrong one is rejected rather than silently written.
4. **Confirm before destructive calls.** `teardown` deletes agents and needs `--yes`.

Run from the repo root: `.claude/skills/test-agent/scripts/test_agents.py <command>`

---

## Step 0 — Where are we pointing, and what exists

```bash
.../test_agents.py status
```

Prints the API base and each of the three agents with its current `provider_id` /
`model_id`, or `NOT PROVISIONED`.

The base URL comes from `TONE_API_BASE`, else `API_DOMAIN` in
`build/kubernetes/envs/staging.env`. Login uses `TONE_STAGING_EMAIL` /
`TONE_STAGING_PASSWORD` from `.env`. If either is missing the script stops and says so —
ask the user rather than guessing an account.

**Report which environment you are about to write to before doing anything.** Staging is
shared.

## Step 1 — Choose the baseline

```bash
.../test_agents.py catalogue
```

Lists every provider in that environment with its model count and kinds. Show the user
what is available for each layer and **ask which to start on** — one provider/model per
layer, plus a `voice_id` for TTS if they want a specific voice.

Pick nothing yourself. The baseline is what every later comparison is measured against.

## Step 2 — Provision

```bash
.../test_agents.py provision \
    --org <name> \
    --stt <provider>/<model> \
    --llm <provider>/<model> \
    --tts <provider>/<model> \
    [--voice-id <id>] \
    [--prompt "..."] [--first-message "..."]
```

`--org` is **required**: provision creates that organisation and puts the agents in it,
so a test run can never add agents to an org you already use. The org id is saved to
`scripts/.org-state.json` keyed by API base, and `status`, `catalogue`, `swap` and
`teardown` switch into it automatically — pass `--org <organization_id>` to any of them
to point at a different one.

Creates `swap-stt` with the baseline, then **clones it twice** into `swap-llm` and
`swap-tts`. Refuses to run if any of the three already exists — use `swap` to change a
layer, or `teardown` first.

There is no separate publish step. `create_agent` writes the config and sets
`published_config_id` in one go, and `clone_agent` promotes the copy it makes, so all
three agents are live the moment they exist.

Keep the prompt short and neutral. A long or clever prompt adds variance that competes
with the thing being measured.

## Step 3 — Swap one layer

```bash
.../test_agents.py swap --layer stt --provider <slug> --model <name>
```

Repoints that layer on the matching agent and prints before/after. The other two agents
are untouched.

The model's `kind` must match the layer — swapping a TTS model into `--layer stt` is
rejected, because it would leave the agent with no working STT and fail at the first
audio frame rather than at swap time.

## Step 4 — Call them

Trigger calls through **tone-test** and compare across the three agents, not across time
on one agent. The transport target is `WS_CALL_TARGET_URL` (staging:
`wss://staging-test.trytone.ai/`).

What to hold constant so the comparison means something: the same script or caller
prompt, the same network path, and calls placed close together. Latency in particular
moves with load, so a swap measured an hour apart is measuring the hour.

## Step 5 — Tear down

```bash
.../test_agents.py teardown          # lists what it would delete
.../test_agents.py teardown --yes    # deletes
```

Without `--yes` it only prints. Deletes are not reversible.

---

## Gotchas

1. **`voice_settings` is TTS.** There is no `tts_settings` column. Writing one is a
   silent no-op.
2. **A layer needs `provider_id` *and* `model_id`.** Both are UUIDs from the catalogue,
   not slugs or names. `swap` resolves them for you; hand-written config must not.
3. **The provider needs an API key row in that org.** Without one the resolver returns no
   spec and the agent runs with that service missing — the call connects and the agent is
   deaf or mute, with no error. If a swap produces silence, check the key before
   suspecting the model.
4. **A model's `kind` is authoritative.** Do not infer the layer from the provider —
   several vendors serve two or three.
5. **`provision` refuses to overwrite.** That is deliberate: silently recreating the
   agents would reset the baseline mid-comparison.
6. **Compare across agents, never across time.** The whole design exists so that two
   configurations can be exercised under the same conditions.
7. **Do not use `/agent_config/upsert_agent_config`.** It casts `agent_id` to `int`
   while `Agent.id` is a UUID, so it 500s on every call (xfail-pinned in
   `test-cases/ee/test_agent_configs.py`). Config writes go through
   `PUT /agent/update_agent?agent_id=<uuid>` with a partial `config` body — only the
   keys you send are written, so a one-layer swap leaves the rest of the config alone.
8. **Check `status` before writing.** These agents live in a shared org on a shared
   dev database; a peer session can be mid-comparison on them. A `swap` or `teardown`
   underneath someone else's run destroys their result.

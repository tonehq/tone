---
name: scripts
description: "Skill for the Scripts area of tone. 77 symbols across 14 files."
---

# Scripts

77 symbols | 14 files | Cohesion: 71%

## When to Use

- Working with code in `scripts/`
- Understanding how run_git_diff, find_repo_root, run work
- Modifying scripts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend/scripts/sync_test_strings.py` | run_git_diff, find_repo_root, HunkStrings, parse_diff_hunks, load_report (+14) |
| `scripts/test_tts_models_and_voices.py` | get_provider, get_tts_models, get_voices, parse_provider_ids, _truncate (+7) |
| `scripts/update_tts_test_status.py` | get_unprocessed_rows, resolve_provider_id, resolve_model_id, get_agent_config, get_reference_agent_config (+5) |
| `frontend/scripts/pr_code_review.py` | run, get_pr_diff, filter_diff, _should_include, load_checklists (+4) |
| `scripts/generate_voice_test_matrix.py` | load_dev_data, _get_rime_model_for_voice, _get_sarvam_model_for_voice, pair_groq, pair_rime (+3) |
| `core/internal/machine.py` | get_machine_id, get_database_id, generate_fingerprint |
| `frontend/src/components/agents/agent-form/promptPage.tsx` | PromptPage, toggleStyle, handleHeadingChange |
| `pipecat/src/pipecat/audio/turn/smart_turn/local_smart_turn_v3.py` | _write_audio_to_wav, _predict_endpoint, truncate_audio_to_last_n_seconds |
| `dev/update_meta_data_schema.py` | load_seed_data, update_meta_data_schemas, main |
| `scripts/update_sarvam_voice_models.py` | get_voice_to_model_map, main |

## Entry Points

Start here when exploring this area:

- **`run_git_diff`** (Function) — `frontend/scripts/sync_test_strings.py:121`
- **`find_repo_root`** (Function) — `frontend/scripts/sync_test_strings.py:134`
- **`run`** (Function) — `frontend/scripts/pr_code_review.py:59`
- **`get_machine_id`** (Function) — `core/internal/machine.py:5`
- **`get_database_id`** (Function) — `core/internal/machine.py:53`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `HunkStrings` | Class | `frontend/scripts/sync_test_strings.py` | 38 |
| `AgentConfig` | Class | `core/models/agent_config.py` | 6 |
| `StringChange` | Class | `frontend/scripts/sync_test_strings.py` | 30 |
| `run_git_diff` | Function | `frontend/scripts/sync_test_strings.py` | 121 |
| `find_repo_root` | Function | `frontend/scripts/sync_test_strings.py` | 134 |
| `run` | Function | `frontend/scripts/pr_code_review.py` | 59 |
| `get_machine_id` | Function | `core/internal/machine.py` | 5 |
| `get_database_id` | Function | `core/internal/machine.py` | 53 |
| `generate_fingerprint` | Function | `core/internal/machine.py` | 57 |
| `PromptPage` | Function | `frontend/src/components/agents/agent-form/promptPage.tsx` | 66 |
| `toggleStyle` | Function | `frontend/src/components/agents/agent-form/promptPage.tsx` | 136 |
| `handleHeadingChange` | Function | `frontend/src/components/agents/agent-form/promptPage.tsx` | 165 |
| `truncate_audio_to_last_n_seconds` | Function | `pipecat/src/pipecat/audio/turn/smart_turn/local_smart_turn_v3.py` | 132 |
| `get_unprocessed_rows` | Function | `scripts/update_tts_test_status.py` | 93 |
| `resolve_provider_id` | Function | `scripts/update_tts_test_status.py` | 103 |
| `resolve_model_id` | Function | `scripts/update_tts_test_status.py` | 110 |
| `get_agent_config` | Function | `scripts/update_tts_test_status.py` | 117 |
| `get_reference_agent_config` | Function | `scripts/update_tts_test_status.py` | 123 |
| `update_agent_config_via_api` | Function | `scripts/update_tts_test_status.py` | 145 |
| `poll_for_completed_calls` | Function | `scripts/update_tts_test_status.py` | 171 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Get` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Test-cases | 17 calls |
| Services | 9 calls |
| Tests | 5 calls |
| Google | 1 calls |
| Asyncio | 1 calls |
| Cartesia | 1 calls |
| Foundational | 1 calls |
| Processors | 1 calls |

## How to Explore

1. `gitnexus_context({name: "run_git_diff"})` — see callers and callees
2. `gitnexus_query({query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details

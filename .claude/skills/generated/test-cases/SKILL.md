---
name: test-cases
description: "Skill for the Test-cases area of tone. 250 symbols across 60 files."
---

# Test-cases

250 symbols | 60 files | Cohesion: 99%

## When to Use

- Working with code in `test-cases/`
- Understanding how test_get_voices_success, test_get_voices_empty, test_get_voices_unauthenticated work
- Modifying test-cases-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `test-cases/test_channel_phone_numbers.py` | test_get_phone_numbers_success, test_get_phone_numbers_empty, test_get_phone_numbers_missing_channel_id, test_get_phone_numbers_invalid_channel_id, test_get_phone_numbers_unauthenticated (+15) |
| `test-cases/test_organizations.py` | test_accept_invitation_success, test_accept_invitation_missing_email, test_accept_invitation_missing_code, test_accept_invitation_invalid_code, test_get_settings_success (+14) |
| `test-cases/test_auth.py` | test_resend_verification_success, test_resend_verification_missing_email, test_verify_email_success, test_verify_email_missing_code, test_verify_email_missing_email (+13) |
| `dev/test_stt_models.py` | load_stt_providers, test_deepgram, test_openai, test_groq, test_sarvam (+9) |
| `test-cases/test_services.py` | test_get_all_services_success, test_get_all_services_filter_by_type, test_get_all_services_empty, test_get_all_services_unauthenticated, test_get_service_success (+8) |
| `test-cases/test_channels.py` | test_get_all_channels_success, test_get_all_channels_empty, test_get_all_channels_unauthenticated, test_get_channel_success, test_get_channel_missing_id (+6) |
| `test-cases/test_agents.py` | test_get_all_agents_success, test_get_all_agents_empty, test_get_all_agents_with_agent_id_filter, test_get_all_agents_unauthenticated, test_get_all_agents_invalid_agent_id_type (+5) |
| `test-cases/test_voices.py` | test_get_voices_success, test_get_voices_empty, test_get_voices_unauthenticated, test_get_voice_by_provider_success, test_get_voice_by_provider_empty (+4) |
| `test-cases/test_service_providers.py` | test_get_all_providers_success, test_get_all_providers_filter_by_type, test_get_all_providers_empty, test_get_all_providers_unauthenticated, test_get_provider_success (+4) |
| `core/services/agent_runner_service.py` | _get_twilio_credentials_from_channel, _get_twilio_credentials_from_api_keys, _get_twilio_credentials, _fetch_twilio_call_info, _get_telnyx_api_key (+4) |

## Entry Points

Start here when exploring this area:

- **`test_get_voices_success`** (Function) — `test-cases/test_voices.py:31`
- **`test_get_voices_empty`** (Function) — `test-cases/test_voices.py:39`
- **`test_get_voices_unauthenticated`** (Function) — `test-cases/test_voices.py:45`
- **`test_get_voice_by_provider_success`** (Function) — `test-cases/test_voices.py:56`
- **`test_get_voice_by_provider_empty`** (Function) — `test-cases/test_voices.py:66`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Agent` | Class | `core/models/agent.py` | 9 |
| `AWSTranscribePresignedURL` | Class | `pipecat/src/pipecat/services/aws/utils.py` | 87 |
| `MessageConversionResult` | Class | `pipecat/src/pipecat/adapters/services/gemini_adapter.py` | 168 |
| `ConvertedMessages` | Class | `pipecat/src/pipecat/adapters/services/anthropic_adapter.py` | 105 |
| `JWTClaims` | Class | `core/middleware/auth.py` | 15 |
| `test_get_voices_success` | Function | `test-cases/test_voices.py` | 31 |
| `test_get_voices_empty` | Function | `test-cases/test_voices.py` | 39 |
| `test_get_voices_unauthenticated` | Function | `test-cases/test_voices.py` | 45 |
| `test_get_voice_by_provider_success` | Function | `test-cases/test_voices.py` | 56 |
| `test_get_voice_by_provider_empty` | Function | `test-cases/test_voices.py` | 66 |
| `test_get_voice_by_provider_service_error` | Function | `test-cases/test_voices.py` | 73 |
| `test_get_voice_by_provider_missing_id` | Function | `test-cases/test_voices.py` | 80 |
| `test_get_voice_by_provider_invalid_id` | Function | `test-cases/test_voices.py` | 84 |
| `test_get_voice_by_provider_unauthenticated` | Function | `test-cases/test_voices.py` | 88 |
| `test_get_all_users_success` | Function | `test-cases/test_users.py` | 15 |
| `test_get_all_users_empty` | Function | `test-cases/test_users.py` | 25 |
| `test_get_all_users_unauthenticated` | Function | `test-cases/test_users.py` | 31 |
| `test_get_all_invited_users_success` | Function | `test-cases/test_users.py` | 42 |
| `test_get_all_invited_users_empty` | Function | `test-cases/test_users.py` | 51 |
| `test_get_all_invited_users_unauthenticated` | Function | `test-cases/test_users.py` | 57 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Telephony_websocket → Query` | cross_community | 6 |
| `Telephony_websocket → Get` | cross_community | 5 |
| `Process_frame → Get` | cross_community | 5 |
| `Proxy_request → Get` | cross_community | 4 |
| `Download_audio → Get` | cross_community | 3 |
| `Run_bot → Agent` | cross_community | 3 |
| `Main → Get` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Services | 8 calls |
| Tests | 3 calls |
| Database | 2 calls |
| Scripts | 2 calls |
| Middleware | 2 calls |
| Foundational | 1 calls |
| Openai_realtime_beta | 1 calls |
| My_service | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_get_voices_success"})` — see callers and callees
2. `gitnexus_query({query: "test-cases"})` — find related execution flows
3. Read key files listed above for implementation details

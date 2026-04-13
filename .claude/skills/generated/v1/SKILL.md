---
name: v1
description: "Skill for the V1 area of tone. 168 symbols across 43 files."
---

# V1

168 symbols | 43 files | Cohesion: 81%

## When to Use

- Working with code in `core/`
- Understanding how get_all_users_for_organization, get_all_invited_users_for_organization, get_all_users_for_organization work
- Modifying v1-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `core/api/v1/organizations.py` | accept_invitation, validate_invitation, accept_invitation_with_password, cancel_invitation, remove_user_from_organization (+8) |
| `ee/api/v1/organizations.py` | invite_user_to_organization, accept_invitation, remove_user_from_organization, update_member_role, get_organization_settings (+6) |
| `ee/api/v1/auth.py` | signup, check_organization_exists, signup_with_firebase, resend_verification_email, verify_user_email (+3) |
| `ee/api/v1/channel_phone_numbers.py` | upsert_channel_phone_number, get_all_channel_phone_numbers, get_phone_numbers_by_channel, get_channel_phone_number, delete_channel_phone_number (+3) |
| `core/api/v1/channel_phone_numbers.py` | upsert_channel_phone_number, get_all_channel_phone_numbers, get_phone_numbers_by_channel, get_channel_phone_number, delete_channel_phone_number (+3) |
| `core/api/v1/auth.py` | signup, signup_with_firebase, resend_verification_email, verify_user_email, login (+1) |
| `ee/api/v1/voices.py` | get_voices, get_voice, get_languages_by_provider, get_voices_by_language, upsert_voice (+1) |
| `core/api/v1/voices.py` | get_voices, get_voice, get_languages_by_provider, get_voices_by_language, upsert_voice (+1) |
| `ee/api/v1/generated_api_keys.py` | upsert_basic_key, upsert_full_key, get_all_keys, get_key, delete_key |
| `core/api/v1/generated_api_keys.py` | upsert_basic_key, upsert_full_key, get_all_keys, get_key, delete_key |

## Entry Points

Start here when exploring this area:

- **`get_all_users_for_organization`** (Function) — `ee/services/auth_service.py:250`
- **`get_all_invited_users_for_organization`** (Function) — `ee/services/auth_service.py:275`
- **`get_all_users_for_organization`** (Function) — `ee/api/v1/users.py:12`
- **`get_all_invited_users_for_organization`** (Function) — `ee/api/v1/users.py:20`
- **`invite_user_to_organization`** (Function) — `ee/api/v1/organizations.py:30`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `EEAuthService` | Class | `ee/services/auth_service.py` | 20 |
| `AuthService` | Class | `core/services/auth_service.py` | 23 |
| `ChannelPhoneNumbersService` | Class | `core/services/channel_phone_numbers_service.py` | 22 |
| `VoiceService` | Class | `core/services/voice_service.py` | 11 |
| `GeneratedApiKeyService` | Class | `core/services/generated_api_key_service.py` | 11 |
| `ServiceConfigService` | Class | `core/services/service_service.py` | 14 |
| `ChannelService` | Class | `core/services/channel_service.py` | 20 |
| `ApiKeyService` | Class | `core/services/api_key_service.py` | 14 |
| `CallLogService` | Class | `core/services/call_log_service.py` | 15 |
| `ServiceProviderService` | Class | `core/services/service_provider_service.py` | 12 |
| `AgentService` | Class | `core/services/agent_service.py` | 55 |
| `ModelService` | Class | `core/services/model_service.py` | 11 |
| `AgentChannelPhoneNumbersService` | Class | `core/services/agent_channel_phone_numbers_service.py` | 38 |
| `get_all_users_for_organization` | Function | `ee/services/auth_service.py` | 250 |
| `get_all_invited_users_for_organization` | Function | `ee/services/auth_service.py` | 275 |
| `get_all_users_for_organization` | Function | `ee/api/v1/users.py` | 12 |
| `get_all_invited_users_for_organization` | Function | `ee/api/v1/users.py` | 20 |
| `invite_user_to_organization` | Function | `ee/api/v1/organizations.py` | 30 |
| `accept_invitation` | Function | `ee/api/v1/organizations.py` | 51 |
| `remove_user_from_organization` | Function | `ee/api/v1/organizations.py` | 61 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Get_audio_url → Config` | cross_community | 4 |
| `Download_audio → Config` | cross_community | 4 |
| `Get_audio_url → CallLogService` | intra_community | 3 |
| `Download_audio → CallLogService` | intra_community | 3 |
| `Download_audio → Get` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Test-cases | 41 calls |
| Services | 7 calls |
| Pipeline | 1 calls |
| Sagemaker | 1 calls |
| Internal | 1 calls |

## How to Explore

1. `gitnexus_context({name: "get_all_users_for_organization"})` — see callers and callees
2. `gitnexus_query({query: "v1"})` — find related execution flows
3. Read key files listed above for implementation details

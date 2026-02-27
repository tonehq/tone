# Impacted APIs Report

> Generated: 2026-02-26
> Comparing: `ea9b495` → `5e49c7c`
> Branch: `dev`
> Commits in range: `339568f`, `8331bf5`, `ec91933`, `0f9bc43`, `44ad9e5`, `5e49c7c`

---

## Summary

| Category | Added | Modified | Deleted |
|----------|-------|----------|---------|
| API Endpoints | 0 | 0 | 0 |
| Service Functions | 0 | 0 | 0 |
| Model Classes | 0 | 0 | 0 |
| Config / Infrastructure | 0 | 1 | 0 |

> **No API endpoint, service function, or model changes** were introduced between these two commits.
> The only Python change is a cleanup in `core/config.py`.

---

## Impacted API Endpoints

None.

---

## Impacted Service Functions

None.

---

## Impacted Models

None.

---

## Config / Infrastructure Changes

### Modified: `core/config.py`

**Change type:** Cleanup / Behaviour fix

| What Changed | Before | After |
|---|---|---|
| `USE_INFISICAL` guard | `if USE_INFISICAL != "true": return {}` — Infisical skipped by default | Guard removed — Infisical is always attempted |
| Debug `print` statements | Two `print()` calls exposed secret key names to stdout | Removed — no more stdout leakage |

**Raw diff:**
```diff
- use_infisical = os.getenv("USE_INFISICAL", "false").lower() == "true"
-
- if not use_infisical:
-     return {}
  try:
      from infisical_sdk import InfisicalSDKClient

- print(f"Fetching secret for key: {key}")
- print(f"Infisical secrets available: {list(infisical_secrets.keys())}")
  return infisical_secrets.get(key) or os.getenv(key, default)
```

**Impact on APIs:** None directly. However:
- Deployments that previously set `USE_INFISICAL=false` to skip secret fetching will now **always** attempt Infisical. If the Infisical SDK is not configured, this may cause a startup error.
- The `try/except` in `get_infisical_secrets()` should catch SDK failures gracefully, so the app should still fall back to environment variables.

---

## Context: What Changed in the Baseline (`ea9b495`)

The commit used as the **starting point** (`ea9b495`) introduced significant API-level changes.
These are NOT included in the diff above (they are the "before" state), but are noted here for context:

### `core/models/channel_phone_numbers.py` — `ChannelPhoneNumbers` model
- **Removed:** `unique=True` constraint on `phone_number` column
- **Migration:** `c7d8e9f0a1b2_allow_phone_number_in_multiple_channels.py`
- **Effect:** The same phone number can now be linked to multiple channels

### `core/services/agent_service.py` — `AgentService._build_agent_response()`
- **Modified:** `phone_number` field in response changed from a single string to an array of objects
  ```python
  # Before
  "phone_number": phone_rows[0].phone_number if phone_rows else None,
  "country_code": phone_rows[0].country_code if phone_rows else None,

  # After
  "phone_number": [{"type": p.provider, "no": p.phone_number} for p in phone_rows],
  ```
- **⚠️ Breaking change for API consumers:** `GET /api/v1/agent/get_all_agents` now returns `phone_number` as an **array** of `{ type, no }` objects instead of a plain string. Any frontend or client code expecting a string will break.

---

## Non-Python Changes in Range

| File | Status | Notes |
|------|--------|-------|
| `.claude/settings.local.json` | Deleted | Removed sensitive local settings |
| `.claude/skills/generate-api-code-documentation/SKILL.md` | Added | New Claude skill |
| `.claude/skills/postman/SKILL.md` | Added | New Claude skill |
| `.gitignore` | Modified | Updated ignore rules |
| `.infisical.json` | Added | Infisical project config |
| `CLAUDE.md` | Modified | Updated Claude instructions |
| `core/Api.md` | Added | API documentation (auto-generated) |
| `postman/agents.postman_collection.json` | Added | Postman collection for agents |
| `postman_collection.json` | Added | Root-level Postman collection |
| `src/pipecat-ai` | Added | New pipecat-ai source |
| `frontend/package-lock.json` | Added | Frontend lock file |
| `frontend/yarn.lock` | Modified | Frontend dependency update |

---

## Files Changed (Python only)

| File | Status | Lines Added | Lines Removed |
|------|--------|-------------|---------------|
| `core/config.py` | Modified | 0 | 5 |

---

## Dependency Impact Chain

```
core/config.py (get_infisical_secrets cleanup)
  └── Settings.__init__() — reads all secrets at startup
      └── DATABASE_URL, JWT_SECRET_KEY, etc.
          └── No direct API endpoint change
          └── ⚠️  Risk: startup failure if Infisical not reachable and no try/except wraps the outer call
```

---

## Recommendations

1. **Verify Infisical fallback** — with the `USE_INFISICAL` guard removed, ensure the `try/except` in `get_infisical_secrets()` handles all failure modes (missing SDK, network timeout, invalid token) without crashing startup.

2. **Update API docs for `phone_number` field** — the `ea9b495` baseline commit changed `GET /api/v1/agent/get_all_agents` response shape. `Api.md` should be updated to reflect that `phone_number` is now `Array<{ type: string, no: string }>`.

3. **Check frontend consumers** — the `AgentFormPage`, `AgentListPage`, and `AssignPhoneNumberModal` were updated in `ea9b495`, but any other consumers of the agents API (mobile apps, external integrations) must handle the new array format.

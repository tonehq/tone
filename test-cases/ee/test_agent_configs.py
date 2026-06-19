"""Tests for Agent Config API endpoints (EE edition).

Source: ee/api/v1/agent_configs.py
Postman: postman_collection/agent_configs.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.

NOTE: This file is intentionally a stub. The previous tests in this module
targeted POST /api/v1/agent_config/upsert_agent_config, which no longer
exists on the EE router (the router currently exposes only a list/get
endpoint). All four test classes (TestUpsertAgentConfigCreate,
TestUpsertAgentConfigUpdate, TestUpsertAgentConfigEdgeCases,
TestUpsertAgentConfigValidation) were removed because every test hit a
404. Add new tests here once the EE router gains create/update endpoints.
"""

"""Unit tests for prompt template-variable substitution.

Pure logic — no DB or network. Run:
    pytest test-cases/test_prompt_variables.py -v -o "addopts="
"""

from core.services.pipeline.params.base import PipelineParams
from core.services.pipeline.prompt_variables import (
    build_call_context, substitute_variables)


class TestSubstituteVariables:
    def test_replaces_known_keys(self):
        ctx = {"caller_number": "+15551234567", "agent_name": "Acme Bot"}
        text = "Hi, this is {{agent_name}} calling {{caller_number}}."
        assert (
            substitute_variables(text, ctx)
            == "Hi, this is Acme Bot calling +15551234567."
        )

    def test_leaves_unknown_tokens_intact(self):
        ctx = {"caller_number": "+1555"}
        text = "Known {{caller_number}}, unknown {{mystery_field}}."
        assert substitute_variables(text, ctx) == "Known +1555, unknown {{mystery_field}}."

    def test_tolerates_inner_whitespace(self):
        ctx = {"agent_name": "Bot"}
        assert substitute_variables("{{ agent_name }}", ctx) == "Bot"

    def test_adjacent_and_repeated_tokens(self):
        ctx = {"a": "1", "b": "2"}
        assert substitute_variables("{{a}}{{b}}{{a}}", ctx) == "121"

    def test_empty_or_none_text_passthrough(self):
        assert substitute_variables("", {"a": "1"}) == ""
        assert substitute_variables(None, {"a": "1"}) is None

    def test_empty_context_passthrough(self):
        assert substitute_variables("{{a}}", {}) == "{{a}}"
        assert substitute_variables("{{a}}", None) == "{{a}}"

    def test_non_string_value_coerced(self):
        assert substitute_variables("n={{count}}", {"count": 3}) == "n=3"

    def test_custom_default_substituted(self):
        # Custom variable {{key|default}} resolves to its default (no context needed).
        assert substitute_variables("Code: {{discount|SAVE10}}", {}) == "Code: SAVE10"
        assert substitute_variables("Code: {{discount|SAVE10}}", None) == "Code: SAVE10"

    def test_empty_custom_default_removes_token(self):
        assert substitute_variables("[{{note|}}]", {}) == "[]"

    def test_system_key_wins_over_inline_default(self):
        # A pipe on a known system key still resolves to the live value.
        ctx = {"caller_number": "+1555"}
        assert substitute_variables("{{caller_number|fallback}}", ctx) == "+1555"

    def test_custom_default_with_context_present(self):
        ctx = {"agent_name": "Acme"}
        assert (
            substitute_variables("{{agent_name}} / {{plan|free}}", ctx) == "Acme / free"
        )

    def test_unknown_without_pipe_left_intact(self):
        assert substitute_variables("{{mystery}}", {}) == "{{mystery}}"


class _FakeAgent:
    def __init__(self, name="Acme", agent_type="inbound"):
        self.name = name
        self.agent_type = agent_type


class TestBuildCallContext:
    def test_resolves_call_data_and_agent(self):
        ctx = build_call_context(
            agent=_FakeAgent(name="Acme", agent_type="outbound"),
            call_data={"from": "+1111", "to": "+2222"},
            transport_type="twilio",
        )
        assert ctx["caller_number"] == "+1111"
        assert ctx["callee_number"] == "+2222"
        assert ctx["agent_name"] == "Acme"
        assert ctx["call_direction"] == "outbound"
        # Date/time always present and well-formed.
        assert len(ctx["current_date"]) == 10  # YYYY-MM-DD
        assert ":" in ctx["current_time"]

    def test_missing_fields_default_to_empty(self):
        ctx = build_call_context(agent=None, call_data=None)
        assert ctx["caller_number"] == ""
        assert ctx["callee_number"] == ""
        assert ctx["agent_name"] == ""
        assert ctx["call_direction"] == ""


class TestPipelineParamsSubstitution:
    def _params(self):
        return PipelineParams(
            llm={"provider_name": "x"},
            messages=[
                {"role": "system", "content": "You are {{agent_name}}. Caller: {{caller_number}}."},
                {"role": "assistant", "content": "Hello {{caller_number}}!"},
            ],
        )

    def test_substitutes_system_and_first_message(self):
        ctx = {"agent_name": "Acme", "caller_number": "+1555"}
        msgs = self._params().messages_with_runtime_context(ctx)
        # Date preamble is prepended to the system message; assert the substituted tail.
        assert msgs[0]["role"] == "system"
        assert "You are Acme. Caller: +1555." in msgs[0]["content"]
        assert msgs[1]["content"] == "Hello +1555!"

    def test_first_message_with_context(self):
        ctx = {"caller_number": "+1555"}
        assert self._params().first_message_with_context(ctx) == "Hello +1555!"

    def test_empty_context_is_date_anchor_only(self):
        params = self._params()
        anchored = params.messages_with_date_anchor()
        same = params.messages_with_runtime_context(None)
        assert same == anchored
        # Unsubstituted tokens remain when no context is supplied.
        assert "{{agent_name}}" in same[0]["content"]

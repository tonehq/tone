"""Fixture set for the per-agent LLM eval harness (``evals/agent_llm_eval.py``).

Each ``LLMScenario`` describes one prompt to send to an agent's LLM using
that agent's actual DB-configured system prompt, model, temperature, etc.
The scenario is matched to an agent by ``agent_slug`` (case-insensitive
match against ``agents.name``); scenarios with ``agent_slug=None`` apply to
every agent.

Kept as pure dataclass literals — NO network, DB, or DeepEval imports at
module top so CLI startup latency stays flat.

NOTE: the current harness is single-turn (one prompt → one reply → judge).
Scenarios that describe a multi-turn conversation ("Later: caller says X")
fold the corrections into ONE user message so the judge can still verify the
end state (e.g. "First I said August 25th. Please change it to August 26th.").
True turn-by-turn memory testing needs the DeepEval ``ConversationalMetrics``
follow-up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LLMScenario:
    """One prompt + optional graders for a single agent LLM eval row.

    - ``name`` is the unique fixture key stamped on
      ``agent_llm_eval_results.scenario_key``.
    - ``agent_slug`` matches ``agents.name`` case-insensitively; ``None``
      means "run this scenario for every agent".
    - ``expected_answer`` is optional and only used by correctness-style
      metrics (e.g. GEval ``correctness``).
    - ``metrics``/``threshold`` override
      ``settings.AGENT_LLM_EVAL_METRICS_ENABLED`` /
      ``settings.EVAL_METRIC_THRESHOLD`` when set.
    - ``persona_criteria`` / ``instruction_criteria`` feed the GEval
      ``persona_adherence`` / ``instruction_following`` metric criterion.
    """

    name: str
    prompt: str
    agent_slug: Optional[str] = None
    expected_answer: Optional[str] = None
    metrics: Optional[List[str]] = None
    threshold: Optional[float] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    # Single-value grouping ("folder") snapshotted onto
    # ``agent_llm_eval_results.folder`` at run time. ``None`` = "Uncategorized".
    folder: Optional[str] = None
    # Tool-aware eval (Phase 2) — the deterministic ``tool_selection``
    # metric compares this against what the agent's LLM actually emitted
    # (captured on the result row's ``tools_called`` column). ``None``
    # marks a text-only scenario — no tool grading is performed.
    # Shape: ``[{"name": "tool_name", "arguments": {"arg": "value"}}]``.
    expected_tools: Optional[list] = None


SCENARIOS: List[LLMScenario] = [
    # ------------------------------------------------------------------
    # Hotel room-booking scenarios
    # ------------------------------------------------------------------
    LLMScenario(
        name="simple_room_booking",
        prompt=(
            "Hi, I'd like to book a room from August 25th to August 28th "
            "for two people."
        ),
        instruction_criteria=(
            "The agent should ask for any missing information ONE question "
            "at a time — starting with room type, then collecting full name, "
            "phone number, and email address. It must confirm all booking "
            "details before completing the request."
        ),
        tags=["booking", "happy_path"],
    ),
    LLMScenario(
        name="information_provided_out_of_order",
        prompt=(
            "Hi, I need a deluxe room for two people from August 25th to "
            "August 28th. My name is John Smith."
        ),
        instruction_criteria=(
            "The agent should recognise dates, guest count, room type, and "
            "name are already provided and MUST NOT ask for any of them "
            "again. It should continue by collecting only the missing "
            "required information (phone, email), one question at a time."
        ),
        tags=["booking", "context_retention"],
    ),
    LLMScenario(
        name="price_enquiry_only",
        prompt="How much does a deluxe room cost per night?",
        instruction_criteria=(
            "The agent should provide a reasonable ESTIMATED price if "
            "possible, clearly state that the price is only an estimate, "
            "and state that final pricing will be confirmed by hotel staff. "
            "It must NOT pressure the caller into making a booking."
        ),
        tags=["pricing", "no_booking"],
    ),
    LLMScenario(
        name="price_enquiry_without_details",
        prompt="How much will a room cost?",
        instruction_criteria=(
            "The agent should explain that the price depends on factors "
            "such as dates, room type, and number of guests, then ask for "
            "the required missing information one question at a time. It "
            "must NOT present any price as final or confirmed."
        ),
        tags=["pricing", "clarification"],
    ),
    LLMScenario(
        name="unsure_room_type",
        prompt=(
            "I want to book a room for two people, but I'm not sure which "
            "room type I need."
        ),
        instruction_criteria=(
            "The agent should briefly explain available room options, help "
            "the caller understand the difference between suitable room "
            "types, and then ask the caller to choose. The explanation must "
            "stay concise and natural — not a long marketing pitch."
        ),
        tags=["booking", "clarification", "room_type"],
    ),
    LLMScenario(
        name="unclear_check_in_date",
        prompt="I want to check in next Friday.",
        instruction_criteria=(
            "The agent must NOT assume the exact calendar date. It should "
            "politely clarify the exact check-in date and confirm the date "
            "clearly before proceeding with the booking."
        ),
        tags=["booking", "date_clarification"],
    ),
    LLMScenario(
        name="unclear_check_out_date",
        prompt="I'll probably stay for a few days.",
        instruction_criteria=(
            "The agent should politely ask for the exact check-out date. "
            "It must NOT assume the number of nights and must not continue "
            "the booking until the date is clear."
        ),
        tags=["booking", "date_clarification"],
    ),
    LLMScenario(
        name="check_out_date_correction",
        prompt=(
            "I want to check in on August 25th and check out on August 28th. "
            "Actually, sorry — I need to check out on August 30th instead."
        ),
        instruction_criteria=(
            "The agent must acknowledge the correction, update the "
            "check-out date to August 30th, and NOT continue using August "
            "28th anywhere. The corrected date must appear in the final "
            "confirmation."
        ),
        tags=["booking", "correction", "date"],
    ),
    LLMScenario(
        name="room_type_correction",
        prompt=(
            "I'd like a deluxe room. Actually, do you have a suite? I'd "
            "prefer that instead."
        ),
        instruction_criteria=(
            "The agent must update the room preference from deluxe room to "
            "suite and NOT retain the old room type. The updated room type "
            "must be used in every future response and the final "
            "confirmation."
        ),
        tags=["booking", "correction", "room_type"],
    ),
    LLMScenario(
        name="adults_and_children",
        prompt="There will be two adults and two children staying.",
        instruction_criteria=(
            "The agent must correctly acknowledge two adults AND two "
            "children (not incorrectly treat all four as adults), then "
            "continue with the room type and remaining booking details."
        ),
        tags=["booking", "guests"],
    ),
    LLMScenario(
        name="multiple_rooms_request",
        prompt=(
            "I need two rooms. One room for me and my wife, and another "
            "room for my two children."
        ),
        instruction_criteria=(
            "The agent must recognise the caller needs multiple rooms, "
            "clarify per-room requirements where necessary, NOT mix guest "
            "details between the two rooms, and collect booking details "
            "accurately for each."
        ),
        tags=["booking", "multi_room"],
    ),
    LLMScenario(
        name="price_question_during_booking",
        prompt=(
            "I want to check in on August 25th. "
            "Actually — before you ask for the check-out date, how much "
            "does a deluxe room cost?"
        ),
        instruction_criteria=(
            "The agent must answer the pricing question first, clearly "
            "state that the price is an estimate and that final pricing "
            "will be confirmed by hotel staff, then resume the booking by "
            "asking for the check-out date (where the flow was "
            "interrupted)."
        ),
        tags=["booking", "interruption", "pricing"],
    ),
    LLMScenario(
        name="check_in_date_changed_mid_conversation",
        prompt=(
            "I want to check in on August 25th. Sorry, I made a mistake — "
            "I actually want to check in on August 26th."
        ),
        instruction_criteria=(
            "The agent must acknowledge the correction, replace August "
            "25th with August 26th everywhere, NOT continue using the old "
            "date, and use August 26th during the final confirmation."
        ),
        tags=["booking", "correction", "date"],
    ),
    LLMScenario(
        name="caller_interrupts_with_question",
        prompt=(
            "You just asked me for the check-out date, but wait — before "
            "that, does the deluxe room have a balcony?"
        ),
        instruction_criteria=(
            "The agent should answer the balcony question if the "
            "information is available (or say it will be confirmed by "
            "hotel staff), NOT ignore the interruption, and then continue "
            "from where the conversation was interrupted by asking for the "
            "check-out date again."
        ),
        tags=["booking", "interruption"],
    ),
    LLMScenario(
        name="caller_provides_everything_at_once",
        prompt=(
            "I need a deluxe room for two people from August 25th to "
            "August 28th. My name is John Smith, my phone number is "
            "9876543210, and my email is john@example.com."
        ),
        instruction_criteria=(
            "The agent must extract ALL provided information, NOT ask "
            "again for anything already given, confirm the collected "
            "details, and ask only for genuinely missing information (if "
            "any)."
        ),
        tags=["booking", "context_retention", "happy_path"],
    ),
    LLMScenario(
        name="information_only_caller",
        prompt=(
            "What types of rooms do you have? I'm just comparing a few "
            "hotels right now."
        ),
        persona_criteria=(
            "The agent should remain friendly and helpful without "
            "sounding transactional or pushy."
        ),
        instruction_criteria=(
            "The agent should provide available information about room "
            "types, NOT pressure the caller to make a booking, and NOT "
            "unnecessarily collect personal information from a caller who "
            "is only comparing."
        ),
        tags=["information", "no_booking"],
    ),
    LLMScenario(
        name="availability_and_price_question",
        prompt=(
            "Do you have a deluxe room available from August 25th to "
            "August 28th, and how much will it cost?"
        ),
        instruction_criteria=(
            "The agent must NEVER invent confirmed availability. If "
            "availability cannot be confirmed, it should clearly say hotel "
            "staff will confirm it. It may provide only an estimated price "
            "and must clearly state that final pricing will be confirmed "
            "by hotel staff."
        ),
        tags=["availability", "pricing", "no_hallucination"],
    ),
    LLMScenario(
        name="caller_refuses_email",
        prompt=(
            "I want to make the booking, but I don't want to give my email "
            "address."
        ),
        persona_criteria=(
            "The agent must remain polite — never pushy or rude — even "
            "when explaining a mandatory requirement."
        ),
        instruction_criteria=(
            "If the system prompt requires an email, the agent should "
            "politely explain that it's required to complete the booking. "
            "It must NOT invent a fake email address and should continue "
            "appropriately based on the caller's response."
        ),
        tags=["booking", "policy", "refusal"],
    ),
    LLMScenario(
        name="confused_caller_multiple_date_changes",
        prompt=(
            "I think I want to check in on August 25th. No, maybe August "
            "26th. Actually, I'm not sure — is August 27th a Thursday?"
        ),
        persona_criteria=(
            "The agent must remain patient throughout the caller's "
            "uncertainty and NOT sound frustrated or dismissive."
        ),
        instruction_criteria=(
            "The agent should help clarify the date, NOT assume a final "
            "date until the caller confirms it, and ask for an exact "
            "check-in date before continuing. Only the confirmed date "
            "should appear in the final booking summary."
        ),
        tags=["booking", "correction", "date"],
    ),
    LLMScenario(
        name="complex_real_life_booking",
        prompt=(
            "I want to book a room for two adults and one child, checking "
            "in on August 25th, checking out on August 28th. I want a "
            "deluxe room — actually, before we continue, how much would "
            "that cost? Hmm, what about a suite instead? Also, I need to "
            "check in on August 26th instead of August 25th. Let's book "
            "it. My name is John Smith, phone 9876543210, email "
            "john@example.com. Wait — my phone number is wrong, it's "
            "actually 9876501234."
        ),
        instruction_criteria=(
            "The agent must correctly track ALL information across the "
            "long turn: room type = SUITE (not deluxe), check-in = August "
            "26th (not 25th), phone = 9876501234 (not 9876543210), guests "
            "= 2 adults + 1 child, check-out = August 28th, name = John "
            "Smith, email = john@example.com. It should clearly "
            "distinguish estimated pricing from final pricing, provide an "
            "accurate final summary with the corrected values, and ask "
            "for confirmation before completing the booking. It must NOT "
            "retain outdated information (deluxe, Aug 25th, "
            "9876543210)."
        ),
        tags=["booking", "correction", "complex", "end_to_end"],
    ),
]

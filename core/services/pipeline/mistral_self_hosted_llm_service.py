from typing import Any, Optional

from loguru import logger

from pipecat.services.openai.llm import BaseOpenAILLMService


def _role_of(message: Any) -> Optional[str]:
    if isinstance(message, dict):
        return message.get("role")
    return getattr(message, "role", None)


def repair_tool_role_order(messages: list) -> list:
    """Insert an empty assistant turn between a tool result and a following user turn.

    mistral_common's validator enforces that a `tool` message is followed by
    `assistant`, never `user`, and rejects the whole request with a 400
    (`InvalidMessageStructureException: Unexpected role 'user' after role 'tool'`).
    Pipecat appends the next user utterance straight after the tool result when the
    bot is interrupted before it can speak, which produces exactly that sequence.

    Only inserts *between* a tool result and a user turn — never at the tail, since
    the validator separately requires the last role to be user or tool, so an
    assistant appended at the end would trade one 400 for another.
    """
    repaired: list = []
    last_index = len(messages) - 1
    for index, message in enumerate(messages):
        repaired.append(message)
        if _role_of(message) != "tool" or index == last_index:
            continue
        if _role_of(messages[index + 1]) == "user":
            repaired.append({"role": "assistant", "content": ""})
    return repaired


class MistralSelfHostedLLMService(BaseOpenAILLMService):
    """BaseOpenAILLMService for self-hosted Mistral served by vLLM in mistral mode.

    `--tokenizer-mode mistral` routes prompt building through mistral_common, whose
    strict message-order validator rejects sequences the OpenAI API accepts.
    """

    def build_chat_completion_params(self, params_from_context) -> dict:
        params = super().build_chat_completion_params(params_from_context)
        messages = params.get("messages")
        if not messages:
            return params
        repaired = repair_tool_role_order(messages)
        if len(repaired) != len(messages):
            logger.debug(
                "{}: repaired mistral message order, inserted {} assistant turn(s) after tool results",
                self,
                len(repaired) - len(messages),
            )
            params["messages"] = repaired
        return params

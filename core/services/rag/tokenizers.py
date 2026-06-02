from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import tiktoken
from loguru import logger
from transformers import AutoTokenizer


class Tokenizer(ABC):
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...


class ApproxTokenizer(Tokenizer):
    def __init__(self, chars_per_token: float = 4.0):
        self._chars_per_token = chars_per_token

    def count_tokens(self, text: str) -> int:
        return max(1, int(len(text) / self._chars_per_token))


class OpenAITokenizer(Tokenizer):
    def __init__(self, model: str = "text-embedding-3-small"):
        self._enc = tiktoken.encoding_for_model(model)

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))
    
    def token_print(self, text: str) -> str:
        return str(self._enc.encode(text))


class HuggingFaceTokenizer(Tokenizer):
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._tok = AutoTokenizer.from_pretrained(model)

    def count_tokens(self, text: str) -> int:
        return len(self._tok.encode(text))

    def token_print(self,text:str) -> str:
        return str(self._tok.encode(text))


def get_tokenizer(model: Optional[str] = None) -> Tokenizer:
    if model:
        try:
            return OpenAITokenizer(model)
        except Exception:
            logger.info("No OpenAI tokenizer for {!r}; falling back to HuggingFace", model)
    try:
        return HuggingFaceTokenizer(model) if (model and "/" in model) else HuggingFaceTokenizer()
    except Exception as e:
        logger.warning("HuggingFace tokenizer unavailable ({}); using ApproxTokenizer", e)
        return ApproxTokenizer()
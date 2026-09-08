import asyncio
import json
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from pipecat.utils.asyncio.task_manager import BaseTaskManager
from pydantic import BaseModel
from tokenizers import Tokenizer

from core.processors.text_turn_detection_turn_stop import (
    TextTurnDetectionUserTurnStopStrategy,
    TurnDecision,
)
from core.utils.llm_context import flatten_message_content

HF_REPO = "livekit/turn-detector"
ONNX_FILENAME = "model_q8.onnx"
MODEL_REVISIONS = {"multilingual": "v0.4.1-intl", "en": "v1.2.2-en"}
MAX_HISTORY_TOKENS = 128
MAX_HISTORY_TURNS = 6

IM_START = "<|im_start|>"
IM_END = "<|im_end|>"
WHITESPACE = re.compile(r"\s+")


class LiveKitTurnDetectorParams(BaseModel):
    model_type: Literal["multilingual", "en"] = "multilingual"
    revision: Optional[str] = None
    threshold: Optional[float] = None
    max_history_turns: int = MAX_HISTORY_TURNS
    max_history_tokens: int = MAX_HISTORY_TOKENS
    cpu_count: int = 1


class LiveKitTurnDetectorModel:
    _cache: Dict[tuple, "LiveKitTurnDetectorModel"] = {}
    _lock = threading.Lock()

    def __init__(self, *, model_type: str, revision: str, cpu_count: int):
        model_path = hf_hub_download(HF_REPO, ONNX_FILENAME, subfolder="onnx", revision=revision)
        tokenizer_path = hf_hub_download(HF_REPO, "tokenizer.json", revision=revision)
        languages_path = hf_hub_download(HF_REPO, "languages.json", revision=revision)
        options = ort.SessionOptions()
        options.intra_op_num_threads = cpu_count
        options.inter_op_num_threads = 1
        options.add_session_config_entry("session.dynamic_block_base", "4")
        self._session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"], sess_options=options
        )
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        with open(languages_path) as f:
            self._languages = json.load(f)
        self._normalize = model_type == "multilingual"

    @classmethod
    def load(cls, params: LiveKitTurnDetectorParams) -> "LiveKitTurnDetectorModel":
        revision = params.revision or MODEL_REVISIONS[params.model_type]
        key = (params.model_type, revision, params.cpu_count)
        with cls._lock:
            model = cls._cache.get(key)
            if model is None:
                model = cls(
                    model_type=params.model_type, revision=revision, cpu_count=params.cpu_count
                )
                cls._cache[key] = model
        return model

    def threshold(self, language: Optional[str]) -> Optional[float]:
        if not language:
            return None
        entry = self._languages.get(language) or self._languages.get(language.split("-")[0])
        return entry["threshold"] if entry else None

    def normalize_text(self, text: str) -> str:
        if not self._normalize or not text:
            return text
        text = unicodedata.normalize("NFKC", text.lower())
        text = "".join(
            ch
            for ch in text
            if not (unicodedata.category(ch).startswith("P") and ch not in ("'", "-"))
        )
        return WHITESPACE.sub(" ", text).strip()

    def format_chat(self, messages: List[Dict[str, Any]]) -> str:
        merged: List[List[str]] = []
        for message in messages:
            content = self.normalize_text(message.get("content") or "")
            if not content:
                continue
            if merged and merged[-1][0] == message["role"]:
                merged[-1][1] = f"{merged[-1][1]} {content}"
            else:
                merged.append([message["role"], content])
        text = "".join(f"{IM_START}{role}\n{content}{IM_END}\n" for role, content in merged)
        return text[: text.rfind(IM_END)]

    def predict(self, messages: List[Dict[str, Any]], max_tokens: int) -> float:
        ids = self._tokenizer.encode(self.format_chat(messages), add_special_tokens=False).ids
        input_ids = np.array([ids[-max_tokens:]], dtype=np.int64)
        outputs = self._session.run(None, {"input_ids": input_ids})
        return float(outputs[0].flatten()[-1])


class LiveKitTurnDetectorUserTurnStopStrategy(TextTurnDetectionUserTurnStopStrategy):
    def __init__(
        self,
        *,
        params: Optional[LiveKitTurnDetectorParams] = None,
        context: Any = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._params = params or LiveKitTurnDetectorParams()
        self._context = context
        self._model: Optional[LiveKitTurnDetectorModel] = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    @property
    def params(self) -> LiveKitTurnDetectorParams:
        return self._params

    @property
    def context(self) -> Any:
        return self._context

    async def setup(self, task_manager: BaseTaskManager):
        await super().setup(task_manager)
        if self._model is None:
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(
                self._executor, LiveKitTurnDetectorModel.load, self._params
            )

    async def cleanup(self):
        await super().cleanup()
        self._executor.shutdown(wait=False)

    async def predict(self, text: str, language: Optional[str]) -> Tuple[TurnDecision, float]:
        model = self._model
        if model is None:
            raise RuntimeError(f"{self} used before setup()")
        messages = self._history() + [{"role": "user", "content": text}]
        messages = messages[-self._params.max_history_turns:]
        loop = asyncio.get_running_loop()
        probability = await loop.run_in_executor(
            self._executor, model.predict, messages, self._params.max_history_tokens
        )
        threshold = self._params.threshold
        if threshold is None:
            threshold = model.threshold(language)
        if threshold is None or probability >= threshold:
            return TurnDecision.COMPLETE, probability
        return TurnDecision.INCOMPLETE, probability

    def _history(self) -> List[Dict[str, Any]]:
        if self._context is None:
            return []
        history = []
        for message in self._context.get_messages():
            if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
                continue
            content = flatten_message_content(message.get("content"))
            if content.strip():
                history.append({"role": message["role"], "content": content})
        return history

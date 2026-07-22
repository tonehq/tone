from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Type

from loguru import logger

from benchmarks.base import BaseBenchmark, BenchmarkResult
from benchmarks.llm_benchmark import LLMBenchmark
from benchmarks.stt_benchmark import STTBenchmark
from benchmarks.tts_benchmark import TTSBenchmark
from core.services.pipeline.service_resolver import _build_service_specs

BENCHMARKS: Dict[str, Type[BaseBenchmark]] = {
    "stt": STTBenchmark,
    "llm": LLMBenchmark,
    "tts": TTSBenchmark,
}

DEFAULT_ORDER = ("stt", "llm", "tts")


def register(service_type: str, benchmark_cls: Type[BaseBenchmark]) -> None:
    BENCHMARKS[service_type.strip().lower()] = benchmark_cls


def get_benchmark_class(service_type: str) -> Type[BaseBenchmark]:
    key = (service_type or "").strip().lower()
    try:
        return BENCHMARKS[key]
    except KeyError:
        raise ValueError(
            f"unknown benchmark '{service_type}' -- available: {', '.join(sorted(BENCHMARKS))}"
        ) from None


def resolve_specs(db, org_id, config) -> Dict[str, Optional[Dict[str, Any]]]:
    llm_spec, stt_spec, tts_spec, _is_s2s = _build_service_specs(db, org_id, config)
    return {"llm": llm_spec, "stt": stt_spec, "tts": tts_spec}


async def run_benchmark(
    service_type: str, spec: Dict[str, Any], **options: Any
) -> BenchmarkResult:
    benchmark_cls = get_benchmark_class(service_type)
    return await benchmark_cls(spec, **options).run()


async def run_triplet(
    specs: Dict[str, Optional[Dict[str, Any]]],
    *,
    service_types: Optional[Iterable[str]] = None,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    **options: Any,
) -> Dict[str, Any]:
    selected: List[str] = list(service_types or DEFAULT_ORDER)
    overrides = overrides or {}
    results: Dict[str, Any] = {}

    for service_type in selected:
        spec = specs.get(service_type)
        if not spec:
            logger.warning("[benchmark] skipping {} -- no resolved spec", service_type)
            results[service_type] = {"error": f"no resolved spec for '{service_type}'"}
            continue
        try:
            result = await run_benchmark(
                service_type, spec, **{**options, **overrides.get(service_type, {})}
            )
            results[service_type] = result.to_dict()
        except Exception as exc:
            logger.exception("[benchmark] {} run failed", service_type)
            results[service_type] = {"error": str(exc)}

    return results

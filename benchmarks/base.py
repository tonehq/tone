from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import fmean
from typing import Any, Dict, List, Optional

from loguru import logger

from core.services.readiness.probe_pipeline import probe_in_pipeline
from pipecat.pipeline.task import PipelineParams

WARMUP_ITERATION = -1


@dataclass
class BenchmarkSample:
    iteration: int
    ok: bool
    elapsed_ms: float
    ttfb_ms: Optional[float] = None
    error: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Latency:
    avg: Optional[float] = None
    p50: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

    @classmethod
    def of(cls, values: List[float]) -> "Latency":
        if not values:
            return cls()
        ordered = sorted(values)
        return cls(
            avg=round(fmean(ordered), 2),
            p50=percentile(ordered, 50),
            p90=percentile(ordered, 90),
            p95=percentile(ordered, 95),
            min=round(ordered[0], 2),
            max=round(ordered[-1], 2),
        )


@dataclass
class BenchmarkResult:
    service_type: str
    provider: str
    model: Optional[str]
    iterations: int
    concurrency: int
    succeeded: int
    failed: int
    ttfb_ms: Latency = field(default_factory=Latency)
    started_at: Optional[str] = None
    duration_s: Optional[float] = None
    throughput_rps: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    samples: List[BenchmarkSample] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def percentile(ordered: List[float], pct: float) -> Optional[float]:
    if not ordered:
        return None
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    value = ordered[low] + (ordered[high] - ordered[low]) * (rank - low)
    return round(value, 2)


class BaseBenchmark(ABC):
    service_type: str = ""
    timeout_s: float = 30.0
    warmup_s: float = 0.0
    end_frame_after_s: Optional[float] = None

    def __init__(
        self,
        spec: Dict[str, Any],
        *,
        iterations: int = 5,
        warmup_iterations: int = 1,
        concurrency: int = 1,
        timeout_s: Optional[float] = None,
    ):
        self.spec = spec
        self.iterations = max(1, iterations)
        self.warmup_iterations = max(0, warmup_iterations)
        self.concurrency = max(1, min(concurrency, self.iterations))
        if timeout_s is not None:
            self.timeout_s = timeout_s
        self.provider = spec.get("provider_name") or "unknown"
        self.model = spec.get("model_name")

    @abstractmethod
    def build_service(self) -> Any:
        ...

    @abstractmethod
    def input_frames(self, service: Any) -> List[Any]:
        ...

    @abstractmethod
    def is_target(self, frame: Any) -> bool:
        ...

    def pipeline_params(self) -> PipelineParams:
        return PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=False,
        )

    def sample_detail(self, _frame: Any) -> Dict[str, Any]:
        return {}

    def _failed(self, iteration: int, elapsed_ms: float, error: str) -> BenchmarkSample:
        return BenchmarkSample(iteration, False, round(elapsed_ms, 2), error=error)

    async def _measure(self, iteration: int) -> BenchmarkSample:
        try:
            service = self.build_service()
        except Exception as exc:
            logger.exception("[benchmark] {} construction failed", self.provider)
            return self._failed(iteration, 0.0, f"construction failed: {exc}")

        if service is None:
            return self._failed(iteration, 0.0, f"no pipecat service for '{self.provider}'")

        try:
            frames = self.input_frames(service)
        except Exception as exc:
            logger.exception("[benchmark] {} input preparation failed", self.provider)
            return self._failed(iteration, 0.0, f"input preparation failed: {exc}")

        timings: Dict[str, float] = {}
        started = time.perf_counter()
        try:
            ok, frame, err = await probe_in_pipeline(
                service,
                frames,
                self.is_target,
                params=self.pipeline_params(),
                timeout_s=self.timeout_s,
                provider=self.provider,
                warmup_s=self.warmup_s,
                end_frame_after_s=self.end_frame_after_s,
                timings=timings,
            )
        except Exception as exc:
            logger.exception("[benchmark] {} {} harness raised", self.service_type, self.provider)
            return self._failed(iteration, (time.perf_counter() - started) * 1000.0, str(exc))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not ok:
            return self._failed(iteration, elapsed_ms, err or "no target frame within budget")

        sent_at, target_at = timings.get("sent_at"), timings.get("target_at")
        ttfb_ms = (target_at - sent_at) * 1000.0 if sent_at and target_at else None
        return BenchmarkSample(
            iteration,
            True,
            round(elapsed_ms, 2),
            ttfb_ms=round(ttfb_ms, 2) if ttfb_ms is not None else None,
            detail=self.sample_detail(frame),
        )

    async def _warmup(self) -> None:
        for attempt in range(self.warmup_iterations):
            logger.info(
                "[benchmark] {} {} warmup {}/{}",
                self.service_type,
                self.provider,
                attempt + 1,
                self.warmup_iterations,
            )
            await self._measure(WARMUP_ITERATION)

    async def _measure_all(self) -> List[BenchmarkSample]:
        if self.concurrency == 1:
            return [await self._measure(i) for i in range(self.iterations)]

        gate = asyncio.Semaphore(self.concurrency)

        async def guarded(index: int) -> BenchmarkSample:
            async with gate:
                return await self._measure(index)

        return list(await asyncio.gather(*(guarded(i) for i in range(self.iterations))))

    async def run(self) -> BenchmarkResult:
        await self._warmup()

        started_at = datetime.now(timezone.utc)
        clock = time.perf_counter()
        samples = await self._measure_all()
        duration_s = time.perf_counter() - clock

        passed = [s for s in samples if s.ok]
        errors = sorted({s.error for s in samples if s.error})
        logger.info(
            "[benchmark] {} {} done ok={}/{} in {:.2f}s",
            self.service_type,
            self.provider,
            len(passed),
            self.iterations,
            duration_s,
        )

        return BenchmarkResult(
            service_type=self.service_type,
            provider=self.provider,
            model=self.model,
            iterations=self.iterations,
            concurrency=self.concurrency,
            succeeded=len(passed),
            failed=self.iterations - len(passed),
            ttfb_ms=Latency.of([s.ttfb_ms for s in passed if s.ttfb_ms is not None]),
            started_at=started_at.isoformat(),
            duration_s=round(duration_s, 3),
            throughput_rps=round(len(passed) / duration_s, 3) if duration_s > 0 else None,
            errors=errors,
            samples=samples,
        )

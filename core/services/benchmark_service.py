from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from loguru import logger

from benchmarks.registry import BENCHMARKS, DEFAULT_ORDER, resolve_specs, run_triplet
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.services.base import BaseService
from core.services.readiness.context import ContextBuilder

MAX_ITERATIONS = 50
MAX_CONCURRENCY = 20


class BenchmarkService(BaseService):
    @staticmethod
    def available_types() -> List[str]:
        return [t for t in DEFAULT_ORDER if t in BENCHMARKS] + [
            t for t in sorted(BENCHMARKS) if t not in DEFAULT_ORDER
        ]

    def _get_agent(self, agent_id: str) -> Agent:
        agent = (
            self.db.query(Agent)
            .filter(
                Agent.id == agent_id,
                Agent.organization_id == self.org_id,
                Agent.deleted_at.is_(None),
            )
            .first()
        )
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def _resolve_config(self, agent: Agent, config_id: Optional[str]) -> AgentConfig:
        config = ContextBuilder(self.db, UUID(str(self.org_id))).resolve_config(agent, config_id)
        if config is None:
            raise HTTPException(
                status_code=400, detail="Agent has no resolvable config version to benchmark"
            )
        return config

    def _validate_types(self, service_types: Optional[List[str]]) -> List[str]:
        if not service_types:
            return list(DEFAULT_ORDER)
        normalised = [t.strip().lower() for t in service_types if t and t.strip()]
        unknown = [t for t in normalised if t not in BENCHMARKS]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown service types: {', '.join(unknown)}. "
                f"available: {', '.join(self.available_types())}",
            )
        return normalised or list(DEFAULT_ORDER)

    async def run(
        self,
        agent_id: str,
        *,
        config_id: Optional[str] = None,
        service_types: Optional[List[str]] = None,
        iterations: int = 5,
        warmup_iterations: int = 1,
        concurrency: int = 1,
        timeout_s: Optional[float] = None,
        prompt: Optional[str] = None,
        sentence: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not 1 <= iterations <= MAX_ITERATIONS:
            raise HTTPException(
                status_code=400, detail=f"iterations must be between 1 and {MAX_ITERATIONS}"
            )
        if not 1 <= concurrency <= MAX_CONCURRENCY:
            raise HTTPException(
                status_code=400, detail=f"concurrency must be between 1 and {MAX_CONCURRENCY}"
            )

        selected = self._validate_types(service_types)
        agent = self._get_agent(agent_id)
        config = self._resolve_config(agent, config_id)

        try:
            specs = resolve_specs(self.db, self.org_id, config)
        except Exception as exc:
            logger.exception("[benchmark] spec resolution failed for agent {}", agent_id)
            raise HTTPException(
                status_code=500, detail=f"Could not resolve service specs: {exc}"
            ) from exc

        overrides: Dict[str, Dict[str, Any]] = {}
        if prompt:
            overrides["llm"] = {"prompt": prompt}
        if sentence:
            overrides["tts"] = {"sentence": sentence}

        options: Dict[str, Any] = {
            "iterations": iterations,
            "warmup_iterations": warmup_iterations,
            "concurrency": concurrency,
        }
        if timeout_s is not None:
            options["timeout_s"] = timeout_s

        logger.info(
            "[benchmark] agent={} config={} services={} iterations={} concurrency={}",
            agent_id,
            config.id,
            selected,
            iterations,
            concurrency,
        )
        results = await run_triplet(
            specs, service_types=selected, overrides=overrides, **options
        )

        return {
            "agent_id": str(agent.id),
            "config_id": str(config.id),
            "requested": {
                "service_types": selected,
                "iterations": iterations,
                "warmup_iterations": warmup_iterations,
                "concurrency": concurrency,
            },
            "results": results,
        }

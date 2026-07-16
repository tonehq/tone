"""Response schemas and shared enums for agent readiness.

These are the JSON-serialisable shapes exposed to HTTP callers. The internal
``CheckContext`` (see ``base.py``) is a dataclass that carries live SQLAlchemy
rows and never crosses the API boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Depth(str, Enum):
    """How intensively to check the agent.

    - ``shallow``: DB reads + local decrypts only. Fast, free, safe on every render.
    - ``deep``: everything shallow does + live probe calls to each provider.
    """

    SHALLOW = "shallow"
    DEEP = "deep"


class Category(str, Enum):
    """Categories the readiness feature reports on.

    Scoped to external services (LLM/STT/TTS providers) and attached resources
    (tools, KBs, MCP servers, phone routing) — the things that can genuinely
    fail at runtime and that the CRUD layer can't validate on save.
    """

    LLM = "llm"
    STT = "stt"
    TTS = "tts"
    PHONE = "phone"
    TOOLS = "tools"
    KNOWLEDGE_BASES = "knowledge_bases"
    MCP_SERVERS = "mcp_servers"


class Severity(str, Enum):
    BLOCKER = "blocker"   # call will fail
    WARNING = "warning"   # call works but degraded
    INFO = "info"         # suggestion


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"   # e.g. STT skipped in S2S mode — not a failure


class OverallStatus(str, Enum):
    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    NOT_READY = "not_ready"


class ResourceRef(BaseModel):
    """Stable pointer to the resource a check failed on, so the UI can navigate."""

    type: str
    id: str


class CheckResult(BaseModel):
    """One inspector's report on one rule.

    ``check_id`` is stable across releases; UIs / analytics key off it.
    ``message`` and ``remediation`` are human-readable strings; free to reword.
    """

    check_id: str
    category: Category
    severity: Severity
    status: Status
    message: str
    remediation: Optional[str] = None
    deep_link: Optional[str] = None
    resource_ref: Optional[ResourceRef] = None
    skip_reason: Optional[str] = None


class ReadinessSummary(BaseModel):
    """Small badge-shaped response used by list endpoints."""

    agent_id: str
    config_id: Optional[str] = None
    overall_status: OverallStatus
    blocker_count: int
    warning_count: int
    info_count: int = 0


class ReadinessReport(BaseModel):
    """Full report returned by ``POST /agent/{id}/readiness``.

    ``summary`` counts pass/fail/skipped-by-severity for quick pill rendering;
    ``checks`` is the flat list every UI surface iterates over.
    """

    agent_id: str
    config_id: Optional[str] = None
    depth: Depth
    overall_status: OverallStatus
    summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts: blockers, warnings, info, skipped, passed",
    )
    checks: List[CheckResult] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_summary(self) -> ReadinessSummary:
        return ReadinessSummary(
            agent_id=self.agent_id,
            config_id=self.config_id,
            overall_status=self.overall_status,
            blocker_count=self.summary.get("blockers", 0),
            warning_count=self.summary.get("warnings", 0),
            info_count=self.summary.get("info", 0),
        )

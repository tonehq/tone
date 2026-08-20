"""Per-agent LLM eval CLI.

Runs the fixture set in ``evals/fixtures/agent_llm_scenarios.py`` (or a
user-supplied override) against one agent's LLM using the agent's actual
published config, scores each scenario with DeepEval, and persists results
to ``agent_llm_eval_results``.

Zero business logic here — all work is delegated to
``AgentLlmEvalService``. This module only:
- parses argv,
- resolves the agent by name/UUID,
- filters scenarios by ``agent_slug`` + ``--tag``,
- prints the scorecard,
- exits non-zero iff any scenario failed the verdict.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
import uuid
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.evals.errors import (  # noqa: E402
    AgentLlmEvalConfigError,
    EvalConfigurationError,
)


_DEFAULT_SCENARIOS_MODULE = "evals.fixtures.agent_llm_scenarios"


def _load_scenarios(dotted_or_path: str) -> list:
    """Import a Python module by dotted path OR file path and return its
    ``SCENARIOS`` list. Raises ``SystemExit`` with an actionable message on
    any failure so the caller sees a one-liner, not a stack trace."""
    module_ref = dotted_or_path or _DEFAULT_SCENARIOS_MODULE
    try:
        if module_ref.endswith(".py") or "/" in module_ref:
            spec = importlib.util.spec_from_file_location(
                "agent_llm_scenarios_override", module_ref
            )
            if spec is None or spec.loader is None:
                raise SystemExit(f"Cannot import scenarios file {module_ref!r}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        else:
            mod = importlib.import_module(module_ref)
    except ImportError as e:
        raise SystemExit(f"Cannot import scenarios module {module_ref!r}: {e}")

    scenarios = getattr(mod, "SCENARIOS", None)
    if not isinstance(scenarios, list):
        raise SystemExit(
            f"{module_ref!r} does not export a SCENARIOS list"
        )
    return scenarios


def _filter_scenarios(scenarios: list, *, agent_name: str, tag: str | None) -> list:
    """Keep scenarios whose ``agent_slug`` is empty (applies to all) or matches
    ``agent_name`` (case-insensitive); optionally narrow by ``--tag``."""
    lowered = agent_name.lower()
    matched = [
        s for s in scenarios
        if s.agent_slug is None or s.agent_slug.lower() == lowered
    ]
    if tag:
        matched = [s for s in matched if tag in (s.tags or [])]
    return matched


def _print_scorecard(agent_name: str, summary) -> None:
    print(f"\n[agent-llm-eval] agent={agent_name} run_id={summary.run_id} "
          f"run_number={summary.run_number}")
    print(f"[agent-llm-eval] status={summary.status} "
          f"pass={summary.summary.get('pass', 0)} "
          f"partial={summary.summary.get('partial', 0)} "
          f"fail={summary.summary.get('fail', 0)} "
          f"pass_rate={summary.summary.get('pass_rate', 0.0):.2%}")
    metric_avgs = {
        k: v for k, v in summary.summary.items() if k.startswith("avg_")
    }
    for name, avg in sorted(metric_avgs.items()):
        print(f"  {name}: {float(avg):.3f}")
    if summary.error:
        print(f"[agent-llm-eval] error: {summary.error}")


def _print_scenario_line(row) -> None:
    """One-line per-scenario summary reading from an
    ``agent_llm_eval_results`` row dict (post-persist)."""
    verdict = (row.get("verdict") or "FAIL")
    key = row.get("scenario_key")
    scores = row.get("metric_scores") or {}
    score_summary = ", ".join(
        f"{n}={float(v['score']):.2f}"
        for n, v in sorted(scores.items())
        if isinstance(v, dict) and v.get("score") is not None
    )
    print(f"  {verdict:<8}{key}  {score_summary}")
    if row.get("answer_error"):
        print(f"        answer_error: {row['answer_error']}")
    if row.get("judge_error"):
        print(f"        judge_error: {row['judge_error']}")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Per-agent LLM eval harness (DeepEval-backed)."
    )
    p.add_argument(
        "--agent",
        required=True,
        help="Agent UUID or name (case-insensitive)",
    )
    p.add_argument("--tag", default=None, help="Filter scenarios by tag")
    p.add_argument(
        "--scenarios",
        default=_DEFAULT_SCENARIOS_MODULE,
        help="Dotted module path OR file path exposing a SCENARIOS list",
    )
    p.add_argument(
        "--judge-model",
        default=None,
        help="Override settings.EVAL_JUDGE_MODEL",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the scorecard without persisting rows",
    )
    p.add_argument(
        "--run-id",
        default=None,
        help="UUID label for the run (default: random). Useful for reruns.",
    )
    args = p.parse_args()

    # Lazy: import service AFTER argparse so `--help` never triggers a
    # DeepEval load transitively.
    from core.database.session import get_db_context
    from core.models.agent import Agent
    from core.services.evals.agent_llm.agent_config_loader import (
        AgentConfigLoader,
    )
    from core.services.evals.agent_llm.service import AgentLlmEvalService

    loader = AgentConfigLoader()

    try:
        with get_db_context() as db:
            try:
                agent_id = loader.resolve_agent_id(db, args.agent)
            except AgentLlmEvalConfigError as e:
                raise SystemExit(str(e))
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent is None:
                # resolve_agent_id just found it — a race (soft-delete
                # in-between) is the only way here. Bail with a clear
                # message instead of letting a NoneType deref fire later.
                raise SystemExit(f"Agent {agent_id} disappeared before eval could start")
            # Capture attributes INSIDE the session — the ORM instance is
            # detached the moment the ``with`` block exits, so reading
            # ``agent.organization_id`` later would raise
            # DetachedInstanceError on lazy-load.
            agent_name = agent.name
            organization_id = agent.organization_id

        scenarios: List = _load_scenarios(args.scenarios)
        matched = _filter_scenarios(scenarios, agent_name=agent_name, tag=args.tag)
        if not matched:
            print(
                f"[agent-llm-eval] no scenarios matched agent={agent_name!r} "
                f"tag={args.tag!r} (loaded={len(scenarios)}) — nothing to do",
                file=sys.stderr,
            )
            return 1

        print(
            f"[agent-llm-eval] agent={agent_name} scenarios={len(matched)} "
            f"tag={args.tag or '-'} dry_run={args.dry_run}"
        )

        if args.dry_run:
            # Dry-run: don't touch the service (which would persist). Just
            # print what we'd run so a developer can eyeball the plan.
            for s in matched:
                print(f"  - {s.name}  ({', '.join(s.tags) or '-'})")
            return 0

        run_id = uuid.UUID(args.run_id) if args.run_id else None
        service = AgentLlmEvalService(agent_loader=loader)
        try:
            with get_db_context() as db:
                summary = service.run_eval(
                    db,
                    agent_id=agent_id,
                    scenarios=matched,
                    triggered_by="cli",
                    judge_model=args.judge_model,
                    run_id=run_id,
                )
        except (AgentLlmEvalConfigError, EvalConfigurationError) as e:
            raise SystemExit(str(e))

        _print_scorecard(agent_name, summary)
        # Pull the per-scenario rows back to print concise per-row lines.
        with get_db_context() as db:
            detail = service.get_run_detail(
                db,
                org_id=organization_id,
                run_id=summary.run_id,
            )
        for row in (detail or {}).get("scenarios", []):
            _print_scenario_line(row)

        return 0 if (summary.status == "completed" and summary.summary.get("fail", 0) == 0) else 1
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"[agent-llm-eval] fatal: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

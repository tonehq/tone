"""EvalService — the single entry point for creating, running, and diffing
RAG evaluations.

Transport-agnostic: methods take a SQLAlchemy session + plain args and return
ORM objects. Every caller (the Procrastinate auto-run task and the
``rag-testing/`` CLI wrappers) goes through this class — question-generation,
retrieval, LLM-as-judge, and per-run persistence live in exactly one place."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.models.eval import Eval
from core.models.eval_result import EvalResult
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.services.evals.errors import (
    EvalGenerationError,
    EvalNotFoundError,
    EvalRunError,
)
from core.services.evals.judge import JudgeService
from core.services.evals.prompt_loader import PromptLoader, render_prompt
from core.services.evals.question_generator import QuestionGeneratorService
from core.services.evals.retrieval_hit import retrieval_hit
from core.services.rag.embedder_factory import build_embedder_from_run
from core.services.rag.errors import EmbeddingProviderUnavailableError
from core.services.rag.factory import get_vector_store
from core.services.rag.provider_keys import ProviderKeyService
from core.services.rag.readers import CompositeReader
from shared.config import settings

_VERDICT_RANK = {"FAIL": 0, "PARTIAL": 1, "PASS": 2}


class EvalService:

    def __init__(
        self,
        *,
        question_generator: Optional[QuestionGeneratorService] = None,
        judge: Optional[JudgeService] = None,
        prompt_loader: Optional[PromptLoader] = None,
        reader: Optional[CompositeReader] = None,
        r2_service: Optional[Any] = None,
    ):
        self._loader = prompt_loader or PromptLoader()
        self._questions = question_generator or QuestionGeneratorService(prompt_loader=self._loader)
        self._judge = judge or JudgeService(prompt_loader=self._loader)
        self._reader = reader or CompositeReader()
        self._r2 = r2_service

    # ── Question-set lifecycle ─────────────────────────────────────────

    def generate_eval(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        model: Optional[str] = None,
        max_chars: Optional[int] = None,
    ) -> Eval:
        """Extract source text for ``upload_id``, generate a Q&A set, upsert the
        ``evals`` row (``UNIQUE(upload_id)`` — regeneration replaces in-place).
        Returns the persisted ``Eval``."""
        model = model or settings.EVAL_GENERATION_MODEL
        max_chars = max_chars or settings.EVAL_MAX_CONTEXT_CHARS

        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if upload is None:
            raise EvalNotFoundError(f"Upload {upload_id} not found")
        if not upload.file_path or not upload.file_type:
            raise EvalGenerationError(
                f"Upload {upload_id} has no file_path/file_type — cannot extract source text"
            )
        kb = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.upload_id == upload_id)
            .first()
        )
        if kb is None:
            raise EvalNotFoundError(
                f"No KnowledgeBase found for upload {upload_id}"
            )

        api_key = ProviderKeyService.require_key(db, org_id, "openai")

        file_bytes = self._download(upload.file_path)
        try:
            document = self._reader.read(file_bytes, upload.file_type)
        except Exception as e:
            logger.exception(
                "[eval] source extraction failed upload={} content_type={}",
                upload_id, upload.file_type,
            )
            raise EvalGenerationError(
                f"Source extraction failed: {type(e).__name__}: {e}"
            ) from e

        payload = self._questions.generate(
            document_text=document.text,
            api_key=api_key,
            model=model,
            max_chars=max_chars,
        )
        questions = payload["questions"]

        existing = db.query(Eval).filter(Eval.upload_id == upload_id).first()
        name = _eval_name(kb.name, upload_id)
        prompt_hash = self._questions.prompt_hash()

        if existing is None:
            eval_row = Eval(
                organization_id=org_id,
                knowledge_base_id=kb.id,
                upload_id=upload_id,
                name=name,
                question_count=len(questions),
                questions=payload,
                generated_by_model=payload["generated_by_model"],
                generation_prompt_hash=prompt_hash,
                status="ready",
                error=None,
            )
            db.add(eval_row)
        else:
            existing.name = name
            existing.question_count = len(questions)
            existing.questions = payload
            existing.generated_by_model = payload["generated_by_model"]
            existing.generation_prompt_hash = prompt_hash
            existing.status = "ready"
            existing.error = None
            eval_row = existing
        db.commit()
        db.refresh(eval_row)
        logger.info(
            "[eval] generated question set eval={} upload={} questions={} model={}",
            eval_row.id, upload_id, len(questions), model,
        )
        return eval_row

    def get_eval_by_upload(
        self, db: Session, *, upload_id: Any, org_id: Any
    ) -> Optional[Eval]:
        return (
            db.query(Eval)
            .filter(Eval.upload_id == upload_id, Eval.organization_id == org_id)
            .first()
        )

    def get_or_generate_eval(
        self, db: Session, *, upload_id: Any, org_id: Any
    ) -> Eval:
        existing = self.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
        if existing is not None and existing.status == "ready":
            return existing
        return self.generate_eval(db, upload_id=upload_id, org_id=org_id)

    # ── Run lifecycle ──────────────────────────────────────────────────

    def run_eval(
        self,
        db: Session,
        *,
        eval_id: Any,
        ingestion_run_id: Any,
        triggered_by: str,
        top_k: Optional[int] = None,
        answer_model: Optional[str] = None,
        judge_model: Optional[str] = None,
    ) -> EvalResult:
        """Execute the Q&A set against the pipeline recipe pinned by
        ``ingestion_run_id`` — the embedder + vector store are rebuilt from the
        run so query and stored vectors are guaranteed compatible.

        Persists a row with ``status=running`` up-front so a partial run is
        visible; updates to ``completed`` / ``failed`` at the end. Never
        re-raises: worker callers (see ``eval_ingestion_run``) rely on this
        method being terminal so a bad eval can't fail the ingestion."""
        if triggered_by not in {"auto", "manual", "cli"}:
            raise ValueError(
                f"triggered_by must be one of 'auto'|'manual'|'cli'; got {triggered_by!r}"
            )
        top_k = top_k or settings.EVAL_TOP_K
        answer_model = answer_model or settings.EVAL_ANSWER_MODEL
        judge_model = judge_model or settings.EVAL_JUDGE_MODEL

        eval_row = db.query(Eval).filter(Eval.id == eval_id).first()
        if eval_row is None:
            raise EvalNotFoundError(f"Eval {eval_id} not found")

        questions = _questions_list(eval_row.questions)
        if not questions:
            raise EvalRunError(
                f"Eval {eval_id} has no questions — regenerate before running"
            )

        run = (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.id == ingestion_run_id)
            .first()
        )
        if run is None:
            raise EvalNotFoundError(f"IngestionPipelineRun {ingestion_run_id} not found")

        next_run_number = (
            db.query(func.coalesce(func.max(EvalResult.run_number), 0) + 1)
            .filter(EvalResult.eval_id == eval_id)
            .scalar()
        )
        result = EvalResult(
            organization_id=eval_row.organization_id,
            eval_id=eval_row.id,
            run_number=int(next_run_number),
            ingestion_run_id=run.id,
            triggered_by=triggered_by,
            top_k=int(top_k),
            answer_model=answer_model,
            judge_model=judge_model,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        logger.info(
            "[eval] running eval={} run_number={} ingestion_run={} top_k={} triggered_by={}",
            eval_row.id, result.run_number, run.id, top_k, triggered_by,
        )

        try:
            api_key = ProviderKeyService.require_key(
                db, eval_row.organization_id, run.embedding_provider
            )
            embedder = build_embedder_from_run(run, api_key=api_key)
            store = get_vector_store(run.vector_store, **(run.vector_store_ref or {}))
            openai_key = ProviderKeyService.require_key(
                db, eval_row.organization_id, "openai"
            )
            answer_template = self._loader.load("answer_from_context.md")

            per_question = []
            for q in questions:
                per_question.append(
                    self._score_one_question(
                        question=q,
                        embedder=embedder,
                        store=store,
                        run=run,
                        top_k=int(top_k),
                        answer_model=answer_model,
                        judge_model=judge_model,
                        answer_template=answer_template,
                        openai_key=openai_key,
                    )
                )

            summary = _summarize(per_question)
            result.per_question = per_question
            result.summary = summary
            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(result)
            logger.info(
                "[eval] completed eval={} run_number={} pass={} fail={} pass_rate={:.2%} hit_rate={:.2%}",
                eval_row.id, result.run_number,
                summary["pass"], summary["fail"],
                summary["pass_rate"], summary["retrieval_hit_rate"],
            )
        except EmbeddingProviderUnavailableError as e:
            self._mark_failed(db, result, str(e))
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[eval] run failed eval={} run_number={}",
                eval_row.id, result.run_number,
            )
            self._mark_failed(db, result, f"{type(e).__name__}: {e}")

        return result

    def list_results(
        self, db: Session, eval_id: Any, *, limit: Optional[int] = None
    ) -> List[EvalResult]:
        q = (
            db.query(EvalResult)
            .filter(EvalResult.eval_id == eval_id)
            .order_by(EvalResult.run_number.desc())
        )
        if limit is not None:
            q = q.limit(limit)
        return list(q)

    def latest_result_for_ingestion_run(
        self, db: Session, ingestion_run_id: Any
    ) -> Optional[EvalResult]:
        return (
            db.query(EvalResult)
            .filter(EvalResult.ingestion_run_id == ingestion_run_id)
            .order_by(EvalResult.started_at.desc())
            .first()
        )

    def compare_results(
        self,
        db: Session,
        baseline_result_id: Any,
        candidate_result_id: Any,
        *,
        score_drop: float = 0.15,
    ) -> dict:
        """Diff two runs. Mirrors the CLI ``compare_runs.py`` output shape so
        the CLI can hand its rendering off to a single call."""
        baseline = db.query(EvalResult).filter(EvalResult.id == baseline_result_id).first()
        candidate = db.query(EvalResult).filter(EvalResult.id == candidate_result_id).first()
        if baseline is None or candidate is None:
            raise EvalNotFoundError(
                f"compare_results: missing row (baseline={baseline_result_id}, "
                f"candidate={candidate_result_id})"
            )
        return _diff_results(baseline, candidate, score_drop=score_drop)

    def compare_latest_two(
        self, db: Session, eval_id: Any, *, score_drop: float = 0.15
    ) -> dict:
        rows = self.list_results(db, eval_id, limit=2)
        if len(rows) < 2:
            raise EvalNotFoundError(
                f"Eval {eval_id} has fewer than 2 completed runs; nothing to compare"
            )
        candidate, baseline = rows[0], rows[1]  # DESC order → [newest, previous]
        return _diff_results(baseline, candidate, score_drop=score_drop)

    # ── Internals ──────────────────────────────────────────────────────

    def _download(self, file_path: str) -> bytes:
        r2 = self._r2 or _default_r2_service()
        return r2.download_file(file_path)

    def _score_one_question(
        self,
        *,
        question: dict,
        embedder,
        store,
        run: IngestionPipelineRun,
        top_k: int,
        answer_model: str,
        judge_model: str,
        answer_template: str,
        openai_key: str,
    ) -> dict:
        import time

        import openai

        qid = question.get("id", "?")
        q_text = question.get("question", "")
        expected = question.get("expected_answer", "")
        expected_snippet = question.get("expected_source_snippet", "")
        category = question.get("category", "unknown")

        t0 = time.monotonic()
        retrieval_error = None
        try:
            q_vec = embedder.embed_query(q_text)
            hits = store.query(
                q_vec,
                top_k=top_k,
                filters={
                    "ingestion_run_id": run.id,
                    "embedding_provider": run.embedding_provider,
                    "embedding_model": run.embedding_model,
                    "embedding_dimensions": run.embedding_dimensions,
                },
            )
            retrieved = [
                {
                    "text": h.text,
                    "score": float(h.score) if h.score is not None else None,
                    "chunk_index": h.metadata.get("chunk_index"),
                    "upload_id": str(h.metadata.get("upload_id", "")),
                }
                for h in hits
            ]
        except Exception as e:  # noqa: BLE001
            logger.exception("[eval] retrieval failed qid={}", qid)
            retrieved = []
            retrieval_error = f"{type(e).__name__}: {e}"

        hit = retrieval_hit(expected_snippet, [c["text"] for c in retrieved])

        answer_error = None
        try:
            client = openai.OpenAI(api_key=openai_key)
            prompt = render_prompt(
                answer_template,
                QUESTION=q_text,
                CONTEXT=_build_context(retrieved),
            )
            resp = client.chat.completions.create(
                model=answer_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            actual_answer = (resp.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            logger.exception("[eval] answer LLM failed qid={} model={}", qid, answer_model)
            actual_answer = ""
            answer_error = f"{type(e).__name__}: {e}"

        verdict = self._judge.judge(
            question=q_text,
            expected_answer=expected,
            actual_answer=actual_answer,
            retrieved_chunks=retrieved,
            api_key=openai_key,
            model=judge_model,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        return {
            "id": qid,
            "category": category,
            "question": q_text,
            "expected_answer": expected,
            "expected_source_snippet": expected_snippet,
            "retrieval_hit": hit,
            "retrieved_chunks": retrieved,
            "actual_answer": actual_answer,
            "judge": verdict,
            "latency_ms": latency_ms,
            "retrieval_error": retrieval_error,
            "answer_error": answer_error,
        }

    def _mark_failed(self, db: Session, result: EvalResult, error: str) -> None:
        result.status = "failed"
        result.error = error
        result.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(result)


def _default_r2_service():
    # Lazy import so the eval service module has no boto3 side-effect on import
    # (test-cases stub the constructor out via the r2_service kwarg).
    from core.services.r2_storage_service import R2StorageService

    return R2StorageService()


def _eval_name(kb_name: Optional[str], upload_id: Any) -> str:
    base = (kb_name or "kb").strip() or "kb"
    suffix = str(upload_id).replace("-", "")[:8]
    return f"{base}-{suffix}"[:255]


def _questions_list(payload: Any) -> List[dict]:
    """Accept either the wrapped payload (``{"questions": [...]}``) or a bare
    list, since older CLI-generated rows nested the list under a top-level
    key and the current generator does the same."""
    if isinstance(payload, dict):
        qs = payload.get("questions")
        if isinstance(qs, list):
            return qs
        return []
    if isinstance(payload, list):
        return payload
    return []


def _build_context(chunks: Iterable[dict]) -> str:
    parts = [f"[chunk {i}] {c.get('text', '')}" for i, c in enumerate(chunks, 1)]
    return "\n\n".join(parts) if parts else "(no chunks retrieved)"


def _summarize(rows: List[dict]) -> dict:
    total = len(rows)
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    hit_count = 0
    corr_sum = 0.0
    gnd_sum = 0.0
    rel_sum = 0.0
    latency_sum = 0
    by_category: dict = {}

    for r in rows:
        judge = r.get("judge") or {}
        v = judge.get("verdict", "FAIL")
        counts[v] = counts.get(v, 0) + 1
        if r.get("retrieval_hit"):
            hit_count += 1
        corr_sum += float(judge.get("correctness", 0) or 0)
        gnd_sum += float(judge.get("groundedness", 0) or 0)
        rel_sum += float(judge.get("relevance", 0) or 0)
        latency_sum += int(r.get("latency_ms", 0) or 0)
        cat = r.get("category", "unknown")
        c = by_category.setdefault(
            cat, {"total": 0, "PASS": 0, "PARTIAL": 0, "FAIL": 0, "hits": 0}
        )
        c["total"] += 1
        c[v] = c.get(v, 0) + 1
        if r.get("retrieval_hit"):
            c["hits"] += 1

    return {
        "total": total,
        "pass": counts["PASS"],
        "partial": counts["PARTIAL"],
        "fail": counts["FAIL"],
        "pass_rate": (counts["PASS"] / total) if total else 0.0,
        "partial_rate": (counts["PARTIAL"] / total) if total else 0.0,
        "fail_rate": (counts["FAIL"] / total) if total else 0.0,
        "retrieval_hit_rate": (hit_count / total) if total else 0.0,
        "avg_correctness": (corr_sum / total) if total else 0.0,
        "avg_groundedness": (gnd_sum / total) if total else 0.0,
        "avg_relevance": (rel_sum / total) if total else 0.0,
        "total_questions": total,
        "duration_ms": latency_sum,
        "by_category": by_category,
    }


def _diff_results(
    baseline: EvalResult, candidate: EvalResult, *, score_drop: float
) -> dict:
    b_rows = _index_by_id(baseline.per_question or [])
    c_rows = _index_by_id(candidate.per_question or [])
    all_ids = sorted(set(b_rows) | set(c_rows))

    per_question_diff: List[dict] = []
    regressions: List[dict] = []
    for qid in all_ids:
        b = b_rows.get(qid)
        c = c_rows.get(qid)
        if b is None:
            per_question_diff.append({"id": qid, "kind": "new", "candidate": c["judge"]["verdict"]})
            continue
        if c is None:
            entry = {"id": qid, "kind": "missing", "baseline": b["judge"]["verdict"]}
            per_question_diff.append(entry)
            regressions.append(entry)
            continue

        b_v = b["judge"]["verdict"]
        c_v = c["judge"]["verdict"]
        b_hit = bool(b.get("retrieval_hit"))
        c_hit = bool(c.get("retrieval_hit"))
        d_corr = c["judge"]["correctness"] - b["judge"]["correctness"]
        d_gnd = c["judge"]["groundedness"] - b["judge"]["groundedness"]
        d_rel = c["judge"]["relevance"] - b["judge"]["relevance"]

        note = None
        is_regression = False
        if _VERDICT_RANK[c_v] < _VERDICT_RANK[b_v]:
            note = f"verdict regression {b_v}→{c_v}"
            is_regression = True
        elif b_hit and not c_hit:
            note = "retrieval_hit dropped"
            is_regression = True
        elif d_corr <= -score_drop:
            note = f"correctness drop {d_corr:+.2f}"
            is_regression = True
        elif d_gnd <= -score_drop:
            note = f"groundedness drop {d_gnd:+.2f}"
            is_regression = True

        entry = {
            "id": qid,
            "baseline_verdict": b_v,
            "candidate_verdict": c_v,
            "baseline_hit": b_hit,
            "candidate_hit": c_hit,
            "delta_correctness": d_corr,
            "delta_groundedness": d_gnd,
            "delta_relevance": d_rel,
            "regression": is_regression,
            "note": note,
        }
        per_question_diff.append(entry)
        if is_regression:
            regressions.append(entry)

    return {
        "baseline": {
            "id": str(baseline.id),
            "run_number": baseline.run_number,
            "started_at": baseline.started_at.isoformat() if baseline.started_at else None,
            "summary": baseline.summary or {},
        },
        "candidate": {
            "id": str(candidate.id),
            "run_number": candidate.run_number,
            "started_at": candidate.started_at.isoformat() if candidate.started_at else None,
            "summary": candidate.summary or {},
        },
        "score_drop_threshold": score_drop,
        "regressions": regressions,
        "regression_count": len(regressions),
        "per_question": per_question_diff,
    }


def _index_by_id(rows: List[dict]) -> dict:
    return {r["id"]: r for r in rows if isinstance(r, dict) and "id" in r}

"""EvalService — the single entry point for creating, running, and diffing
RAG evaluations.

Transport-agnostic: methods take a SQLAlchemy session + plain args and return
lightweight summary objects (never HTTP-shaped). Every caller (the
Procrastinate auto-run task and the ``rag-testing/`` CLI wrappers) goes
through this class — question-generation, retrieval, LLM-as-judge, and
persistence live in exactly one place.

Persistence shape (post row-per-question refactor):
- ``evals`` — one row per question. A doc that produces 50 questions
  becomes 50 rows keyed by ``(upload_id, external_id)``. Regeneration
  deletes every row for the upload and inserts the new batch.
- ``eval_results`` — one row per scored answer. All rows in one run share
  ``run_id`` (a UUID stamped by this service) plus the
  per-``(upload_id, ingestion_run_id)`` ``run_number`` so a batch is
  addressable as a unit for summary / compare queries.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import Float, case, cast, func
from sqlalchemy.orm import Session

from core.models.eval import Eval
from core.models.eval_result import EvalResult
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.knowledge_base_chunk import KnowledgeBaseChunk
from core.models.upload import Upload
from core.services.evals.csv_import import (
    EvalCsvParseError,
    parse_eval_questions_csv,
)
from core.services.evals.errors import (
    EvalGenerationError,
    EvalNotFoundError,
    EvalRunError,
)
from core.services.evals.judge import JudgeService
from core.services.evals.judge_factory import build_judge_service
from core.services.evals.prompt_loader import PromptLoader, render_prompt
from core.services.evals.question_generator import QuestionGeneratorService
from core.services.evals.retrieval_hit import retrieval_hit
from core.services.llm.chat_complete import chat_complete, resolve_provider
from core.services.llm.errors import LLMProviderKeyMissingError
from core.services.org_settings import load_eval_settings_for_org
from core.services.rag.embedder_factory import build_embedder_from_run
from core.services.rag.errors import EmbeddingProviderUnavailableError
from core.services.rag.factory import get_vector_store
from core.services.rag.provider_keys import ProviderKeyService
from core.services.rag.readers import CompositeReader
from shared.config import settings

_VERDICT_RANK = {"FAIL": 0, "PARTIAL": 1, "PASS": 2}

# DeepEval metrics we surface in per-run summaries (SQL AVG over the JSONB
# scorecard) and in the compare view's per-question deltas. ``correctness``
# is intentionally omitted — it already flows through the mapped
# ``correctness`` column and its avg is exposed as ``avg_correctness``.
_DEEPEVAL_SUMMARY_METRICS: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "contextual_precision",
    "contextual_recall",
    "contextual_relevancy",
    "hallucination",
)

# Legacy summary keys derived from the mapped columns — the per-scorecard
# aggregation loop skips these names so it can't overwrite them with a
# semantically different value pulled from the DeepEval scorecard.
_LEGACY_AVG_KEYS: frozenset[str] = frozenset({"correctness", "groundedness", "relevance"})

# Metrics where a HIGHER score is WORSE (DeepEval's hallucination fraction).
# Regression semantics for these are inverted: a positive delta (more
# hallucination) is a regression, a negative delta (less hallucination) is
# an improvement.
_INVERTED_SUMMARY_METRICS: frozenset[str] = frozenset({"hallucination"})
_RESERVED_QUESTION_KEYS = {
    "id",
    "question",
    "expected_answer",
    "expected_source_snippet",
    "category",
}


@dataclass
class EvalSetSummary:
    """Snapshot of the question set for one upload — derived from row counts,
    not a stored parent row. ``question_count == 0`` means "no set exists"."""

    upload_id: UUID
    organization_id: UUID
    knowledge_base_id: Optional[UUID]
    question_count: int
    generated_by_model: Optional[str]
    generation_prompt_hash: Optional[str]


@dataclass
class EvalRunSummary:
    """Snapshot of one eval run (batch of scored answers). Identity is
    ``run_id`` (UUID stamped across every row of the batch); ``run_number`` is
    the per-``(upload_id, ingestion_run_id)`` sequence for human ordering."""

    run_id: UUID
    upload_id: UUID
    ingestion_run_id: Optional[UUID]
    run_number: int
    triggered_by: str
    top_k: int
    answer_model: Optional[str]
    judge_model: Optional[str]
    status: str  # 'completed' | 'failed'
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: dict = field(default_factory=dict)


class EvalService:

    def __init__(
        self,
        *,
        question_generator: Optional[QuestionGeneratorService] = None,
        judge: Optional[object] = None,
        prompt_loader: Optional[PromptLoader] = None,
        reader: Optional[CompositeReader] = None,
        r2_service: Optional[Any] = None,
    ):
        self._loader = prompt_loader or PromptLoader()
        self._questions = question_generator or QuestionGeneratorService(prompt_loader=self._loader)
        # Judge is duck-typed on ``judge(**kwargs) -> dict``. Concrete engine
        # (DeepEval / legacy) is picked by ``build_judge_service`` from
        # ``settings.EVAL_JUDGE_ENGINE`` — but ONLY on first access via
        # ``self.judge`` so a FastAPI request that constructs EvalService()
        # just to read run summaries never imports DeepEval (which triggers
        # OTel hijack, nest_asyncio, and telemetry beacons). Tests may pass a
        # MagicMock/instance directly, in which case no factory call happens.
        self._injected_judge: Optional[object] = judge
        self._reader = reader or CompositeReader()
        self._r2 = r2_service

    @property
    def _judge(self) -> object:
        """Lazily build the judge on first use so read-only routes never
        transitively import DeepEval."""
        if self._injected_judge is None:
            self._injected_judge = build_judge_service(prompt_loader=self._loader)
        return self._injected_judge

    # ── Question-set lifecycle ─────────────────────────────────────────

    def generate_eval(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        model: Optional[str] = None,
        max_chars: Optional[int] = None,
        ingestion_run_id: Optional[Any] = None,
    ) -> EvalSetSummary:
        """Extract source text for ``upload_id``, generate a Q&A set, replace
        any existing questions for the upload with the new batch. Returns an
        ``EvalSetSummary``.

        When ``ingestion_run_id`` is provided, source text is reconstructed by
        concatenating the already-persisted ``knowledge_base_chunks`` for that
        run (ordered by ``chunk_index``) — avoiding a redundant R2 download +
        docling re-parse and, more importantly, making the question-generator
        see the exact same text the retriever will hit at run time. When
        omitted (manual CLI / tests), the original R2 + reader path is used.
        """
        # Per-org overrides (DB → env → hardcoded default). Callers may still
        # pin an explicit model / max_chars via kwargs — those win, matching
        # the pre-resolver contract used by CLI tests. Explicit ``None`` from
        # the caller is the "no override" signal (not falsy 0 / "" — those
        # are intentional test values a caller might pass).
        org_eval_cfg = load_eval_settings_for_org(db, org_id)
        if model is None:
            model = org_eval_cfg.generation_model
        if max_chars is None:
            max_chars = org_eval_cfg.max_context_chars

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

        api_key = _require_llm_key(db, org_id, model)

        source_mode = "chunks" if ingestion_run_id is not None else "source_file"
        logger.info(
            "[eval] generate_eval start upload={} org={} content_type={} model={} max_chars={} source={}",
            upload_id, org_id, upload.file_type, model, max_chars, source_mode,
        )

        if ingestion_run_id is not None:
            chunks = (
                db.query(KnowledgeBaseChunk)
                .filter(
                    KnowledgeBaseChunk.ingestion_run_id == ingestion_run_id,
                    KnowledgeBaseChunk.organization_id == org_id,
                )
                .order_by(KnowledgeBaseChunk.chunk_index.asc())
                .all()
            )
            if not chunks:
                raise EvalGenerationError(
                    f"Ingestion run {ingestion_run_id} has no chunks — cannot generate eval"
                )
            document_text = "\n\n".join(c.chunk_text for c in chunks)
            logger.info(
                "[eval] generate_eval assembled {} chunks ({} chars) upload={} run={}",
                len(chunks), len(document_text), upload_id, ingestion_run_id,
            )
        else:
            try:
                file_bytes = self._download(upload.file_path)
            except Exception:
                logger.exception(
                    "[eval] R2 download failed upload={} path={}",
                    upload_id, upload.file_path,
                )
                raise
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
            document_text = document.text

        payload = self._questions.generate(
            document_text=document_text,
            api_key=api_key,
            model=model,
            max_chars=max_chars,
        )
        questions = payload["questions"]
        prompt_hash = self._questions.prompt_hash()

        return self._persist_question_set(
            db,
            upload_id=upload_id,
            org_id=org_id,
            knowledge_base_id=kb.id,
            questions=questions,
            generated_by_model=payload["generated_by_model"],
            generation_prompt_hash=prompt_hash,
        )

    def import_eval(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        questions: List[dict],
        source_key: str,
        name: Optional[str] = None,  # kept for signature parity; not persisted
    ) -> EvalSetSummary:
        """Pre-seed a question set from an already-authored Q&A list — no LLM
        generation. Used by the benchmark CLI so a standard dataset (HotpotQA,
        TAT-QA, ...) can flow through the same ingestion + auto-eval pipeline
        customers use, but scored against gold Q&A instead of LLM-generated.
        ``source_key`` is stamped on ``generated_by_model`` as an audit trail —
        mirrors ``generate_eval`` but obvious enough at read time that these
        rows are not LLM-authored. Replaces any existing rows for the upload."""
        del name  # legacy no-op — set names are no longer persisted
        if not questions:
            raise EvalGenerationError("import_eval requires a non-empty questions list")

        kb = (
            db.query(KnowledgeBase)
            .filter(KnowledgeBase.upload_id == upload_id)
            .first()
        )
        if kb is None:
            raise EvalNotFoundError(
                f"No KnowledgeBase found for upload {upload_id}"
            )

        summary = self._persist_question_set(
            db,
            upload_id=upload_id,
            org_id=org_id,
            knowledge_base_id=kb.id,
            questions=list(questions),
            generated_by_model=source_key,
            generation_prompt_hash=None,
        )
        logger.info(
            "[eval] imported gold question set upload={} questions={} source={}",
            upload_id, summary.question_count, source_key,
        )
        return summary

    def add_questions_manual(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        questions: List[dict],
    ) -> EvalSetSummary:
        """Append user-authored questions to the eval set for ``upload_id`` —
        does NOT wipe existing rows (unlike ``import_eval`` / ``generate_eval``
        which replace the whole set). Every appended row is stamped with
        ``generated_by_model='manual'`` so the audit trail distinguishes
        hand-authored rows from LLM-generated / benchmark-imported ones.

        Backend-enforced validation (never trust the caller):
        - ``questions`` must be non-empty.
        - each question needs a non-empty ``question`` and ``expected_answer``.
        - the KB for ``upload_id`` must exist.

        Row identity: ``(upload_id, external_id)`` is unique. When the caller
        supplies an ``id``/``external_id`` it's honoured (and rejected on
        collision); otherwise a stable ``manual-<uuid>`` id is minted.
        ``question_ord`` continues from the current max for the upload so
        appended rows sort AFTER existing ones."""
        if not questions:
            raise EvalGenerationError(
                "add_questions_manual requires a non-empty questions list"
            )

        cleaned: List[dict] = []
        seen_external_ids: set[str] = set()
        for idx, raw in enumerate(questions):
            if not isinstance(raw, dict):
                raise EvalGenerationError(
                    f"question at index {idx} must be an object"
                )
            q_text = str(raw.get("question") or "").strip()
            expected = str(raw.get("expected_answer") or "").strip()
            if not q_text:
                raise EvalGenerationError(
                    f"question at index {idx} is missing 'question'"
                )
            if not expected:
                raise EvalGenerationError(
                    f"question at index {idx} is missing 'expected_answer'"
                )
            snippet_raw = raw.get("expected_source_snippet")
            snippet = str(snippet_raw).strip() if snippet_raw else None
            category_raw = raw.get("category")
            category = str(category_raw).strip() if category_raw else None
            external_id = str(raw.get("id") or raw.get("external_id") or "").strip()
            if external_id and external_id in seen_external_ids:
                raise EvalGenerationError(
                    f"duplicate external_id {external_id!r} in payload"
                )
            if external_id:
                seen_external_ids.add(external_id)
            extras = {
                k: v for k, v in raw.items()
                if k not in _RESERVED_QUESTION_KEYS and k != "external_id"
            } or None
            cleaned.append(
                {
                    "question": q_text,
                    "expected_answer": expected,
                    "expected_source_snippet": snippet,
                    "category": category,
                    "external_id": external_id or None,
                    "extras": extras,
                }
            )

        kb = (
            db.query(KnowledgeBase)
            .filter(
                KnowledgeBase.upload_id == upload_id,
                KnowledgeBase.organization_id == org_id,
            )
            .first()
        )
        if kb is None:
            raise EvalNotFoundError(
                f"No KnowledgeBase found for upload {upload_id}"
            )

        ord_row = (
            db.query(func.coalesce(func.max(Eval.question_ord), -1))
            .filter(Eval.upload_id == upload_id, Eval.organization_id == org_id)
            .scalar()
        )
        next_ord = int(ord_row) + 1

        existing_ids = {
            row[0]
            for row in db.query(Eval.external_id).filter(
                Eval.upload_id == upload_id,
                Eval.organization_id == org_id,
            )
        }
        collisions = seen_external_ids & existing_ids
        if collisions:
            raise EvalGenerationError(
                f"external_id already exists for upload: {sorted(collisions)}"
            )

        rows: List[dict] = []
        for offset, q in enumerate(cleaned):
            external_id = q["external_id"] or f"manual-{uuid.uuid4().hex[:12]}"
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "knowledge_base_id": kb.id,
                    "upload_id": upload_id,
                    "external_id": external_id,
                    "question_ord": next_ord + offset,
                    "question": q["question"],
                    "expected_answer": q["expected_answer"],
                    "expected_source_snippet": q["expected_source_snippet"],
                    "category": q["category"],
                    "generated_by_model": "manual",
                    "generation_prompt_hash": None,
                    "extras": q["extras"],
                }
            )
        db.bulk_insert_mappings(Eval, rows)
        db.commit()
        logger.info(
            "[eval] appended manual question set upload={} added={} next_ord={}",
            upload_id, len(rows), next_ord,
        )

        summary = self.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
        if summary is None:
            raise EvalGenerationError(
                "add_questions_manual: post-insert summary missing"
            )
        return summary

    def add_questions_from_csv(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        csv_bytes: bytes,
    ) -> EvalSetSummary:
        """Append CSV-authored questions to the eval set for ``upload_id``.
        Thin adapter around :meth:`add_questions_manual` — the CSV is parsed
        into the SAME question-dict shape, then handed to the manual path so
        both entry points share identical validation (required fields,
        external_id collisions, kb existence) and audit tag
        (``generated_by_model='manual'``).

        Raises ``EvalGenerationError`` when the CSV parses but no valid
        questions can be extracted (empty ``question``/``expected_answer``,
        collisions with existing rows, etc.) — mirrors the errors the manual
        endpoint already surfaces to callers."""
        try:
            questions = parse_eval_questions_csv(csv_bytes)
        except EvalCsvParseError as e:
            raise EvalGenerationError(str(e)) from e
        return self.add_questions_manual(
            db,
            upload_id=upload_id,
            org_id=org_id,
            questions=questions,
        )

    def update_question(
        self,
        db: Session,
        *,
        question_id: Any,
        org_id: Any,
        patch: dict,
    ) -> Eval:
        """Update whitelisted fields on one question row. Org-scoped so a
        caller from another tenant gets ``EvalNotFoundError`` even with a
        valid ``question_id``. Fields not present in ``patch`` are left
        unchanged; explicit ``None`` clears optional fields
        (``expected_source_snippet``, ``category``)."""
        row = (
            db.query(Eval)
            .filter(Eval.id == question_id, Eval.organization_id == org_id)
            .first()
        )
        if row is None:
            raise EvalNotFoundError(f"Question {question_id} not found")

        if "question" in patch:
            q_text = str(patch.get("question") or "").strip()
            if not q_text:
                raise EvalGenerationError("'question' cannot be empty")
            row.question = q_text
        if "expected_answer" in patch:
            expected = str(patch.get("expected_answer") or "").strip()
            if not expected:
                raise EvalGenerationError("'expected_answer' cannot be empty")
            row.expected_answer = expected
        if "expected_source_snippet" in patch:
            v = patch.get("expected_source_snippet")
            row.expected_source_snippet = (str(v).strip() or None) if v else None
        if "category" in patch:
            v = patch.get("category")
            row.category = (str(v).strip() or None) if v else None

        db.commit()
        db.refresh(row)
        logger.info(
            "[eval] updated question id={} upload={} fields={}",
            row.id, row.upload_id, sorted(patch.keys()),
        )
        return row

    def delete_question(
        self,
        db: Session,
        *,
        question_id: Any,
        org_id: Any,
    ) -> None:
        """Delete one question row (cascades to its ``eval_results`` rows).
        Org-scoped."""
        row = (
            db.query(Eval)
            .filter(Eval.id == question_id, Eval.organization_id == org_id)
            .first()
        )
        if row is None:
            raise EvalNotFoundError(f"Question {question_id} not found")
        upload_id = row.upload_id
        db.delete(row)
        db.commit()
        logger.info("[eval] deleted question id={} upload={}", question_id, upload_id)

    def get_eval_by_upload(
        self, db: Session, *, upload_id: Any, org_id: Any
    ) -> Optional[EvalSetSummary]:
        """Return a summary of the question set for ``upload_id``, or ``None``
        if no questions have been generated yet."""
        row = (
            db.query(
                Eval.knowledge_base_id,
                func.count(Eval.id).label("question_count"),
                func.max(Eval.generated_by_model).label("generated_by_model"),
                func.max(Eval.generation_prompt_hash).label("generation_prompt_hash"),
            )
            .filter(Eval.upload_id == upload_id, Eval.organization_id == org_id)
            .group_by(Eval.knowledge_base_id)
            .first()
        )
        if row is None or row.question_count == 0:
            return None
        return EvalSetSummary(
            upload_id=upload_id,
            organization_id=org_id,
            knowledge_base_id=row.knowledge_base_id,
            question_count=int(row.question_count),
            generated_by_model=row.generated_by_model,
            generation_prompt_hash=row.generation_prompt_hash,
        )

    def list_questions(
        self, db: Session, *, upload_id: Any, org_id: Any
    ) -> List[Eval]:
        """Return the ordered ``Eval`` ORM rows for one upload — the internal
        seam every runner uses so ordering + org-scoping live in one place."""
        return list(
            db.query(Eval)
            .filter(Eval.upload_id == upload_id, Eval.organization_id == org_id)
            .order_by(Eval.question_ord.asc())
            .all()
        )

    def get_or_generate_eval(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        ingestion_run_id: Optional[Any] = None,
    ) -> EvalSetSummary:
        existing = self.get_eval_by_upload(db, upload_id=upload_id, org_id=org_id)
        if existing is not None and existing.question_count > 0:
            return existing
        return self.generate_eval(
            db,
            upload_id=upload_id,
            org_id=org_id,
            ingestion_run_id=ingestion_run_id,
        )

    # ── Run lifecycle ──────────────────────────────────────────────────

    def run_eval(
        self,
        db: Session,
        *,
        upload_id: Any,
        ingestion_run_id: Any,
        triggered_by: str,
        top_k: Optional[int] = None,
        answer_model: Optional[str] = None,
        judge_model: Optional[str] = None,
    ) -> EvalRunSummary:
        """Execute every question for ``upload_id`` against the pipeline recipe
        pinned by ``ingestion_run_id``. Every scored answer is written as one
        ``eval_results`` row, tagged with the same ``run_id`` UUID + the next
        per-``(upload_id, ingestion_run_id)`` ``run_number``.

        Never re-raises: worker callers (see ``eval_ingestion_run``) rely on
        this method being terminal so a bad eval can't fail the ingestion.
        On mid-run crash the completed rows are still persisted and a failed
        ``EvalRunSummary`` is returned."""
        if triggered_by not in {"auto", "manual", "cli"}:
            raise ValueError(
                f"triggered_by must be one of 'auto'|'manual'|'cli'; got {triggered_by!r}"
            )

        questions = self._questions_scoped(db, upload_id=upload_id)
        if not questions:
            raise EvalRunError(
                f"Upload {upload_id} has no eval questions — regenerate before running"
            )
        organization_id = questions[0].organization_id

        # Resolve per-org overrides now that the org is known (DB → env →
        # hardcoded default). Explicit kwargs from the caller (CLI / API
        # override) still win — same precedence as before, just the
        # fallback source is org-aware instead of env-only. ``None`` from
        # the caller is the "no override" signal (not falsy 0 / "" — those
        # are intentional test values a caller might pass).
        org_eval_cfg = load_eval_settings_for_org(db, organization_id)
        if top_k is None:
            top_k = org_eval_cfg.top_k
        if answer_model is None:
            answer_model = org_eval_cfg.answer_model
        if judge_model is None:
            judge_model = org_eval_cfg.judge_model

        # Build the judge for this run. Tests pin a MagicMock via
        # ``EvalService(judge=...)`` — honor that so unit suites don't need
        # the resolver. In production the judge is engine + threshold +
        # metrics scoped to the resolved org config so per-org overrides
        # take effect on the SAME run they were saved on.
        if self._injected_judge is not None:
            run_judge = self._injected_judge
        else:
            run_judge = build_judge_service(
                prompt_loader=self._loader,
                engine=org_eval_cfg.judge_engine,
                metrics_enabled=org_eval_cfg.metrics_enabled,
                metric_threshold=org_eval_cfg.metric_threshold,
            )

        run = (
            db.query(IngestionPipelineRun)
            .filter(IngestionPipelineRun.id == ingestion_run_id)
            .first()
        )
        if run is None:
            raise EvalNotFoundError(f"IngestionPipelineRun {ingestion_run_id} not found")

        next_run_number = int(
            db.query(func.coalesce(func.max(EvalResult.run_number), 0) + 1)
            .filter(
                EvalResult.ingestion_run_id == run.id,
                EvalResult.eval_id.in_([q.id for q in questions]),
            )
            .scalar()
        )
        run_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)
        run_summary = EvalRunSummary(
            run_id=run_id,
            upload_id=upload_id,
            ingestion_run_id=run.id,
            run_number=next_run_number,
            triggered_by=triggered_by,
            top_k=int(top_k),
            answer_model=answer_model,
            judge_model=judge_model,
            status="running",
            error=None,
            started_at=started_at,
            completed_at=None,
            summary={},
        )

        logger.info(
            "[eval] running run_id={} upload={} run_number={} ingestion_run={} questions={} "
            "top_k={} answer_model={} judge_model={} triggered_by={}",
            run_id, upload_id, next_run_number, run.id, len(questions),
            top_k, answer_model, judge_model, triggered_by,
        )

        # Snapshot every attribute we still need AFTER the LLM loop while the
        # ORM rows are attached, then close the caller's session so no pool
        # connection is held across the long (10+ minute) LLM loop — Neon's
        # idle_in_transaction_session_timeout would drop it and both the
        # follow-up query AND the outer ``with`` block's implicit rollback
        # would explode.
        embedding_provider_val = run.embedding_provider
        vector_store_val = run.vector_store
        vector_store_ref_val = dict(run.vector_store_ref or {})
        question_dtos = [_question_to_dto(q) for q in questions]
        db.close()

        scored_rows: List[dict] = []
        try:
            # Fresh short-lived session ONLY for the key lookups; released
            # immediately so nothing is held during the LLM loop below.
            from core.database.session import SessionLocal
            with SessionLocal() as tmp:
                api_key = ProviderKeyService.require_key(
                    tmp, organization_id, embedding_provider_val
                )
                answer_key = _require_llm_key(tmp, organization_id, answer_model)
                judge_key = _require_llm_key(tmp, organization_id, judge_model)
            embedder = build_embedder_from_run(run, api_key=api_key)
            store = get_vector_store(vector_store_val, **vector_store_ref_val)
            answer_template = self._loader.load("answer_from_context.md")

            total_q = len(question_dtos)
            # Progress every N questions (or on the last one). Without this, a
            # 200-question eval that hangs looks identical to one that's just
            # slow — the periodic tick tells you it's alive AND how it's going.
            progress_every = max(1, total_q // 10) if total_q else 1
            for idx, q in enumerate(question_dtos):
                scored = self._score_one_question(
                    question=q,
                    embedder=embedder,
                    store=store,
                    run=run,
                    top_k=int(top_k),
                    answer_model=answer_model,
                    judge_model=judge_model,
                    answer_template=answer_template,
                    answer_key=answer_key,
                    judge_key=judge_key,
                    judge=run_judge,
                )
                scored_rows.append(scored)
                done = idx + 1
                if done % progress_every == 0 or done == total_q:
                    passes = sum(1 for r in scored_rows if (r.get("judge") or {}).get("verdict") == "PASS")
                    fails = sum(1 for r in scored_rows if (r.get("judge") or {}).get("verdict") == "FAIL")
                    logger.info(
                        "[eval] progress run_id={} run_number={} question={}/{} pass_so_far={} fail_so_far={}",
                        run_id, next_run_number, done, total_q, passes, fails,
                    )

            completed_at = datetime.now(timezone.utc)
            self._persist_result_batch(
                organization_id=organization_id,
                run_id=run_id,
                ingestion_run_id=run.id,
                run_number=next_run_number,
                triggered_by=triggered_by,
                top_k=int(top_k),
                answer_model=answer_model,
                judge_model=judge_model,
                started_at=started_at,
                completed_at=completed_at,
                scored_rows=scored_rows,
                question_dtos=question_dtos,
                statuses=["completed"] * len(question_dtos),
            )
            run_summary.status = "completed"
            run_summary.completed_at = completed_at
            run_summary.summary = _summarize_scored_rows(scored_rows)
            logger.info(
                "[eval] completed run_id={} run_number={} pass={} fail={} pass_rate={:.2%} hit_rate={:.2%}",
                run_id, next_run_number,
                run_summary.summary["pass"], run_summary.summary["fail"],
                run_summary.summary["pass_rate"], run_summary.summary["retrieval_hit_rate"],
            )
        except EmbeddingProviderUnavailableError as e:
            self._mark_failed(
                run_summary=run_summary,
                organization_id=organization_id,
                question_dtos=question_dtos,
                scored_rows=scored_rows,
                error=str(e),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "[eval] run failed run_id={} run_number={}",
                run_id, next_run_number,
            )
            self._mark_failed(
                run_summary=run_summary,
                organization_id=organization_id,
                question_dtos=question_dtos,
                scored_rows=scored_rows,
                error=f"{type(e).__name__}: {e}",
            )

        return run_summary

    def list_runs(
        self, db: Session, *, upload_id: Any, limit: Optional[int] = None
    ) -> List[EvalRunSummary]:
        """Return each run's aggregate summary, newest first."""
        return self._runs_for_upload(db, upload_id=upload_id, limit=limit)

    def latest_result_for_ingestion_run(
        self, db: Session, ingestion_run_id: Any
    ) -> Optional[EvalRunSummary]:
        row = (
            db.query(EvalResult.run_id, func.max(EvalResult.started_at).label("started_at"))
            .filter(EvalResult.ingestion_run_id == ingestion_run_id)
            .group_by(EvalResult.run_id)
            .order_by(func.max(EvalResult.started_at).desc())
            .first()
        )
        if row is None:
            return None
        return self._build_run_summary(db, run_id=row.run_id)

    def latest_summaries_by_ingestion(
        self,
        db: Session,
        *,
        org_id: Any,
        upload_id: Any,
        ingestion_run_ids: Iterable[Any],
    ) -> dict:
        """For each ingestion run id in ``ingestion_run_ids``, return the latest
        eval batch summary (``EvalRunSummary``). ONE aggregated SQL query — used
        by the KB Ingestion-Runs table to paint the per-row "Evals" chip
        without an N+1. Rows without any eval batch are simply absent from the
        returned map so the caller can render "—"."""
        ids = [i for i in ingestion_run_ids if i is not None]
        if not ids:
            return {}
        rows = _run_grouped_query(
            db,
            upload_id=upload_id,
            organization_id=org_id,
            ingestion_run_ids=ids,
        ).all()
        # Multiple batches per ingestion run are possible (manual re-runs);
        # keep only the newest — the grouped query already orders DESC by
        # started_at, so the first one we see per key wins.
        by_ingestion: dict = {}
        for r in rows:
            key = str(r.ingestion_run_id) if r.ingestion_run_id else None
            if key is None or key in by_ingestion:
                continue
            by_ingestion[key] = _row_to_run_summary(r)
        return by_ingestion

    def list_runs_for_ingestion(
        self,
        db: Session,
        *,
        org_id: Any,
        upload_id: Any,
        ingestion_run_id: Any,
    ) -> List[EvalRunSummary]:
        """Every eval batch that scored the given ingestion run — newest first.
        Powers the drawer's run-picker."""
        rows = _run_grouped_query(
            db,
            upload_id=upload_id,
            organization_id=org_id,
            ingestion_run_ids=[ingestion_run_id],
        ).all()
        return [_row_to_run_summary(r) for r in rows]

    def get_run_detail(
        self, db: Session, *, org_id: Any, run_id: Any
    ) -> Optional[dict]:
        """Return the summary + per-question scored rows for one eval batch.
        Org-scoped: only rows belonging to ``org_id`` are considered so a
        caller from another tenant sees ``None``."""
        summary_row = _run_grouped_query(
            db, run_id=run_id, organization_id=org_id
        ).first()
        if summary_row is None:
            return None
        summary = _row_to_run_summary(summary_row)
        questions = self._scored_rows_for_run(db, run_id=run_id, org_id=org_id)
        return {"summary": summary, "questions": questions}

    def compare_results(
        self,
        db: Session,
        baseline_run_id: Any,
        candidate_run_id: Any,
        *,
        score_drop: float = 0.15,
    ) -> dict:
        """Diff two runs identified by ``run_id`` UUIDs. Same output shape as
        the pre-refactor implementation so ``compare_runs.py`` needs no
        changes beyond the id it passes in."""
        baseline = self._build_run_summary(db, run_id=baseline_run_id)
        candidate = self._build_run_summary(db, run_id=candidate_run_id)
        if baseline is None or candidate is None:
            raise EvalNotFoundError(
                f"compare_results: missing run (baseline={baseline_run_id}, "
                f"candidate={candidate_run_id})"
            )
        baseline_rows = self._scored_rows_for_run(db, run_id=baseline_run_id)
        candidate_rows = self._scored_rows_for_run(db, run_id=candidate_run_id)
        return _diff_scored_rows(
            baseline_summary=baseline,
            candidate_summary=candidate,
            baseline_rows=baseline_rows,
            candidate_rows=candidate_rows,
            score_drop=score_drop,
        )

    def compare_latest_two(
        self, db: Session, *, upload_id: Any, score_drop: float = 0.15
    ) -> dict:
        runs = self._runs_for_upload(db, upload_id=upload_id, limit=2)
        if len(runs) < 2:
            raise EvalNotFoundError(
                f"Upload {upload_id} has fewer than 2 completed runs; nothing to compare"
            )
        candidate, baseline = runs[0], runs[1]  # DESC → [newest, previous]
        return self.compare_results(
            db,
            baseline_run_id=baseline.run_id,
            candidate_run_id=candidate.run_id,
            score_drop=score_drop,
        )

    # ── Internals ──────────────────────────────────────────────────────

    def _download(self, file_path: str) -> bytes:
        r2 = self._r2 or _default_r2_service()
        return r2.download_file(file_path)

    def _questions_scoped(self, db: Session, *, upload_id: Any) -> List[Eval]:
        return list(
            db.query(Eval)
            .filter(Eval.upload_id == upload_id)
            .order_by(Eval.question_ord.asc())
            .all()
        )

    def _persist_question_set(
        self,
        db: Session,
        *,
        upload_id: Any,
        org_id: Any,
        knowledge_base_id: Any,
        questions: List[dict],
        generated_by_model: Optional[str],
        generation_prompt_hash: Optional[str],
    ) -> EvalSetSummary:
        """Replace every question for ``upload_id`` with the new batch. Cascade
        drops any existing ``eval_results`` rows for the deleted questions."""
        db.query(Eval).filter(Eval.upload_id == upload_id).delete(
            synchronize_session=False
        )
        rows = []
        for idx, q in enumerate(questions):
            extras = {
                k: v for k, v in q.items() if k not in _RESERVED_QUESTION_KEYS
            } or None
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "knowledge_base_id": knowledge_base_id,
                    "upload_id": upload_id,
                    "external_id": str(q.get("id") or f"q{idx + 1}"),
                    "question_ord": idx,
                    "question": str(q.get("question", "")),
                    "expected_answer": str(q.get("expected_answer", "")),
                    "expected_source_snippet": q.get("expected_source_snippet") or None,
                    "category": q.get("category"),
                    "generated_by_model": generated_by_model,
                    "generation_prompt_hash": generation_prompt_hash,
                    "extras": extras,
                }
            )
        if rows:
            db.bulk_insert_mappings(Eval, rows)
        db.commit()
        logger.info(
            "[eval] persisted question set upload={} questions={} model={}",
            upload_id, len(rows), generated_by_model,
        )
        return EvalSetSummary(
            upload_id=upload_id,
            organization_id=org_id,
            knowledge_base_id=knowledge_base_id,
            question_count=len(rows),
            generated_by_model=generated_by_model,
            generation_prompt_hash=generation_prompt_hash,
        )

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
        answer_key: str,
        judge_key: str,
        judge: Optional[object] = None,
    ) -> dict:
        eval_id = question["eval_id"]
        qid = question.get("id", "?")
        q_text = question.get("question", "")
        expected = question.get("expected_answer", "")
        expected_snippet = question.get("expected_source_snippet", "")
        category = question.get("category", "unknown")

        t0 = time.monotonic()
        retrieval_error = None
        try:
            t_ret = time.monotonic()
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
            top_score = retrieved[0]["score"] if retrieved else None
            logger.debug(
                "[eval] retrieved qid={} candidates={} top_score={} elapsed_ms={}",
                qid, len(retrieved), top_score, int((time.monotonic() - t_ret) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("[eval] retrieval failed qid={}", qid)
            retrieved = []
            retrieval_error = f"{type(e).__name__}: {e}"

        hit = retrieval_hit(expected_snippet, [c["text"] for c in retrieved])

        answer_error = None
        try:
            t_ans = time.monotonic()
            prompt = render_prompt(
                answer_template,
                QUESTION=q_text,
                CONTEXT=_build_context(retrieved),
            )
            actual_answer = chat_complete(
                model=answer_model,
                api_key=answer_key,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                json_mode=False,
            )
            logger.debug(
                "[eval] answer qid={} model={} chars={} elapsed_ms={}",
                qid, answer_model, len(actual_answer),
                int((time.monotonic() - t_ans) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("[eval] answer LLM failed qid={} model={}", qid, answer_model)
            actual_answer = ""
            answer_error = f"{type(e).__name__}: {e}"

        t_judge = time.monotonic()
        # Prefer the per-run judge (built with resolved org overrides).
        # Falls back to the lazily-built engine-from-env for direct
        # ``_score_one_question`` callers that pre-date the org resolver.
        active_judge = judge if judge is not None else self._judge
        verdict = active_judge.judge(
            question=q_text,
            expected_answer=expected,
            actual_answer=actual_answer,
            retrieved_chunks=retrieved,
            api_key=judge_key,
            model=judge_model,
        )
        logger.debug(
            "[eval] judge qid={} verdict={} correctness={:.2f} elapsed_ms={}",
            qid, verdict.get("verdict"), float(verdict.get("correctness", 0.0) or 0.0),
            int((time.monotonic() - t_judge) * 1000),
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        return {
            "eval_id": eval_id,
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

    def _mark_failed(
        self,
        *,
        run_summary: EvalRunSummary,
        organization_id: Any,
        question_dtos: List[dict],
        scored_rows: List[dict],
        error: str,
    ) -> None:
        logger.warning(
            "[eval] marking run_id={} failed error={}", run_summary.run_id, error,
        )
        # Rows we DID score before the crash still get persisted; remaining
        # questions get placeholder ``status=failed`` rows so the run's shape
        # (N rows for N questions) is preserved for downstream aggregation.
        scored_ids = {r["eval_id"] for r in scored_rows}
        statuses = ["completed"] * len(scored_rows)
        remaining = [q for q in question_dtos if q["eval_id"] not in scored_ids]
        for q in remaining:
            scored_rows.append(
                {
                    "eval_id": q["eval_id"],
                    "id": q["id"],
                    "category": q.get("category"),
                    "retrieval_hit": False,
                    "retrieved_chunks": None,
                    "actual_answer": None,
                    "judge": {},
                    "latency_ms": None,
                    "retrieval_error": None,
                    "answer_error": None,
                    "run_error": error,
                }
            )
            statuses.append("failed")
        completed_at = datetime.now(timezone.utc)
        try:
            self._persist_result_batch(
                organization_id=organization_id,
                run_id=run_summary.run_id,
                ingestion_run_id=run_summary.ingestion_run_id,
                run_number=run_summary.run_number,
                triggered_by=run_summary.triggered_by,
                top_k=run_summary.top_k,
                answer_model=run_summary.answer_model,
                judge_model=run_summary.judge_model,
                started_at=run_summary.started_at,
                completed_at=completed_at,
                scored_rows=scored_rows,
                question_dtos=question_dtos,
                statuses=statuses,
            )
        except Exception:
            logger.exception(
                "[eval] _mark_failed persist failed run_id={}", run_summary.run_id,
            )
        run_summary.status = "failed"
        run_summary.error = error
        run_summary.completed_at = completed_at
        run_summary.summary = _summarize_scored_rows(
            [r for r, s in zip(scored_rows, statuses) if s == "completed"]
        )

    def _persist_result_batch(
        self,
        *,
        organization_id: Any,
        run_id: UUID,
        ingestion_run_id: Optional[Any],
        run_number: int,
        triggered_by: str,
        top_k: int,
        answer_model: Optional[str],
        judge_model: Optional[str],
        started_at: Optional[datetime],
        completed_at: Optional[datetime],
        scored_rows: List[dict],
        question_dtos: List[dict],
        statuses: List[str],
    ) -> None:
        """Bulk-insert every scored answer on a brand-new session so we never
        inherit a broken pool connection from the LLM-loop session."""
        del question_dtos  # eval_id already stamped on each scored row
        if not scored_rows:
            return
        rows = []
        for scored, status in zip(scored_rows, statuses):
            judge = scored.get("judge") or {}
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "eval_id": scored["eval_id"],
                    "ingestion_run_id": ingestion_run_id,
                    "run_id": run_id,
                    "run_number": run_number,
                    "triggered_by": triggered_by,
                    "top_k": top_k,
                    "answer_model": answer_model,
                    "judge_model": judge_model,
                    "status": status,
                    "actual_answer": scored.get("actual_answer"),
                    "retrieval_hit": bool(scored.get("retrieval_hit")),
                    "retrieved_chunks": scored.get("retrieved_chunks"),
                    "verdict": judge.get("verdict"),
                    "correctness": _to_float(judge.get("correctness")),
                    "groundedness": _to_float(judge.get("groundedness")),
                    "relevance": _to_float(judge.get("relevance")),
                    "judge_reasoning": judge.get("reasoning"),
                    "metric_scores": judge.get("metric_scores"),
                    "latency_ms": scored.get("latency_ms"),
                    "retrieval_error": scored.get("retrieval_error"),
                    "answer_error": scored.get("answer_error"),
                    "started_at": started_at,
                    "completed_at": completed_at,
                }
            )
        from core.database.session import SessionLocal
        with SessionLocal() as fresh:
            fresh.bulk_insert_mappings(EvalResult, rows)
            fresh.commit()
        logger.info(
            "[eval] persisted run_id={} rows={} completed={} failed={}",
            run_id, len(rows), statuses.count("completed"), statuses.count("failed"),
        )

    def _runs_for_upload(
        self, db: Session, *, upload_id: Any, limit: Optional[int] = None
    ) -> List[EvalRunSummary]:
        rows = _run_grouped_query(db, upload_id=upload_id).all()
        summaries = [_row_to_run_summary(r) for r in rows]
        if limit is not None:
            summaries = summaries[:limit]
        return summaries

    def _build_run_summary(
        self, db: Session, *, run_id: Any
    ) -> Optional[EvalRunSummary]:
        row = _run_grouped_query(db, run_id=run_id).first()
        if row is None:
            return None
        return _row_to_run_summary(row)

    def _scored_rows_for_run(
        self, db: Session, *, run_id: Any, org_id: Optional[Any] = None
    ) -> List[dict]:
        """Return the joined ``(EvalResult, Eval)`` rows for one run as plain
        dicts — this is what the diff helper consumes. ``org_id`` is optional
        for CLI callers; user-facing APIs pass it so cross-tenant reads are
        impossible even if a caller guesses a ``run_id``."""
        q = (
            db.query(EvalResult, Eval)
            .join(Eval, Eval.id == EvalResult.eval_id)
            .filter(EvalResult.run_id == run_id)
        )
        if org_id is not None:
            q = q.filter(EvalResult.organization_id == org_id)
        joined = q.order_by(Eval.question_ord.asc()).all()
        return [_result_row_to_dict(r, e) for r, e in joined]


def _default_r2_service():
    # Lazy import so the eval service module has no boto3 side-effect on import
    # (test-cases stub the constructor out via the r2_service kwarg).
    from core.services.r2_storage_service import R2StorageService

    return R2StorageService()


def _require_llm_key(db: Session, org_id: Any, model: str) -> str:
    """Resolve the API key for the provider implied by ``model``.

    Bridges the eval flow to the shared LLM router: the router infers the
    provider from the model prefix, ``ProviderKeyService`` fetches the org's
    key row for that slug. Raises ``LLMProviderKeyMissingError`` (not the
    embedding-specific error) so the eval-run row's ``error`` reads
    "No API key configured for provider 'X' (needed by model 'Y')".
    """
    provider = resolve_provider(model)
    key = ProviderKeyService.get_key(db, org_id, provider)
    if not key:
        raise LLMProviderKeyMissingError(
            f"No API key configured for provider {provider!r} "
            f"(needed by model {model!r})"
        )
    return key


def _question_to_dto(row: Eval) -> dict:
    return {
        "eval_id": row.id,
        "id": row.external_id,
        "question": row.question,
        "expected_answer": row.expected_answer,
        "expected_source_snippet": row.expected_source_snippet or "",
        "category": row.category or "unknown",
    }


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_context(chunks: Iterable[dict]) -> str:
    parts = [f"[chunk {i}] {c.get('text', '')}" for i, c in enumerate(chunks, 1)]
    return "\n\n".join(parts) if parts else "(no chunks retrieved)"


def _summarize_scored_rows(rows: List[dict]) -> dict:
    """Roll up the in-memory scored-row list — used at the tail of ``run_eval``
    so the returned ``EvalRunSummary`` carries the same summary payload the
    CLI used to read off ``result.summary``.

    Averages ``avg_<metric>`` are emitted for every DeepEval metric that
    appears in at least one row's ``judge.metric_scores``; legacy
    ``avg_correctness``/``avg_groundedness``/``avg_relevance`` keep working
    off the mapped columns so pre-DeepEval consumers see no change.
    """
    total = len(rows)
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    hit_count = 0
    corr_sum = 0.0
    gnd_sum = 0.0
    rel_sum = 0.0
    latency_sum = 0
    by_category: dict = {}
    # Per-DeepEval-metric aggregates. Denominator is per-metric so a metric
    # that only appears on some rows doesn't get diluted by rows that
    # skipped it (legacy-judge rows carry no scorecard).
    metric_sums: dict[str, float] = {}
    metric_counts: dict[str, int] = {}

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
        for name, entry in (judge.get("metric_scores") or {}).items():
            if not isinstance(entry, dict):
                continue
            # Skip names that would clobber the mapped-column averages
            # computed above — ``avg_correctness`` etc. must stay derived
            # from the same source as their ``EvalResult`` column to keep
            # trends comparable across engine flips.
            if name in _LEGACY_AVG_KEYS:
                continue
            score = entry.get("score")
            if score is None:
                continue
            metric_sums[name] = metric_sums.get(name, 0.0) + float(score)
            metric_counts[name] = metric_counts.get(name, 0) + 1
        cat = r.get("category") or "unknown"
        c = by_category.setdefault(
            cat, {"total": 0, "PASS": 0, "PARTIAL": 0, "FAIL": 0, "hits": 0}
        )
        c["total"] += 1
        c[v] = c.get(v, 0) + 1
        if r.get("retrieval_hit"):
            c["hits"] += 1

    summary = {
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
    for name, sum_ in metric_sums.items():
        cnt = metric_counts.get(name, 0)
        summary[f"avg_{name}"] = (sum_ / cnt) if cnt else 0.0
    return summary


def _run_grouped_query(
    db: Session,
    *,
    upload_id: Any = None,
    run_id: Any = None,
    organization_id: Any = None,
    ingestion_run_ids: Optional[Iterable[Any]] = None,
):
    """Aggregate ``eval_results`` rows into one row per run, computing the
    summary via SQL so we never buffer every answer into memory just to
    render a per-run tally.

    Optional filters (used by the KB drawer / column endpoints):
    - ``organization_id``: tenant-scope the query.
    - ``ingestion_run_ids``: narrow to batches that scored one (or several)
      ingestion runs — powers the per-ingestion "Evals" chip in the UI."""
    # Every row of the same ``run_id`` shares the same batch-level metadata
    # (upload/org/ingestion_run/run_number/triggered_by/top_k/models/timestamps)
    # by construction — the service writes them uniformly in ``run_eval``. So
    # they can go straight into GROUP BY instead of being aggregated. This also
    # side-steps ``MAX(uuid)`` which not every Postgres install has.
    # Per-metric AVG over the JSONB scorecard. Rows without a scorecard
    # (legacy-judge / pre-migration rows) contribute NULL so the AVG
    # ignores them — a clean env-flip back to the legacy judge doesn't
    # dilute historical DeepEval averages.
    metric_avg_cols = [
        func.coalesce(
            func.avg(
                cast(
                    EvalResult.metric_scores[metric_name]["score"].astext,
                    Float,
                )
            ),
            0.0,
        ).label(f"avg_{metric_name}")
        for metric_name in _DEEPEVAL_SUMMARY_METRICS
    ]
    q = (
        db.query(
            EvalResult.run_id.label("run_id"),
            Eval.upload_id.label("upload_id"),
            EvalResult.organization_id.label("organization_id"),
            EvalResult.ingestion_run_id.label("ingestion_run_id"),
            EvalResult.run_number.label("run_number"),
            EvalResult.triggered_by.label("triggered_by"),
            EvalResult.top_k.label("top_k"),
            EvalResult.answer_model.label("answer_model"),
            EvalResult.judge_model.label("judge_model"),
            EvalResult.started_at.label("started_at"),
            EvalResult.completed_at.label("completed_at"),
            func.count(EvalResult.id).label("total"),
            func.sum(case((EvalResult.verdict == "PASS", 1), else_=0)).label("pass_count"),
            func.sum(case((EvalResult.verdict == "PARTIAL", 1), else_=0)).label("partial_count"),
            func.sum(case((EvalResult.verdict == "FAIL", 1), else_=0)).label("fail_count"),
            func.sum(case((EvalResult.retrieval_hit.is_(True), 1), else_=0)).label("hit_count"),
            func.sum(case((EvalResult.status == "failed", 1), else_=0)).label("failed_status_count"),
            func.coalesce(func.avg(EvalResult.correctness), 0.0).label("avg_correctness"),
            func.coalesce(func.avg(EvalResult.groundedness), 0.0).label("avg_groundedness"),
            func.coalesce(func.avg(EvalResult.relevance), 0.0).label("avg_relevance"),
            func.coalesce(func.sum(EvalResult.latency_ms), 0).label("duration_ms"),
            *metric_avg_cols,
        )
        .join(Eval, Eval.id == EvalResult.eval_id)
        .group_by(
            EvalResult.run_id,
            Eval.upload_id,
            EvalResult.organization_id,
            EvalResult.ingestion_run_id,
            EvalResult.run_number,
            EvalResult.triggered_by,
            EvalResult.top_k,
            EvalResult.answer_model,
            EvalResult.judge_model,
            EvalResult.started_at,
            EvalResult.completed_at,
        )
        .order_by(EvalResult.started_at.desc())
    )
    if upload_id is not None:
        q = q.filter(Eval.upload_id == upload_id)
    if run_id is not None:
        q = q.filter(EvalResult.run_id == run_id)
    if organization_id is not None:
        q = q.filter(EvalResult.organization_id == organization_id)
    if ingestion_run_ids is not None:
        # ``.in_([])`` returns no rows, which is exactly what we want when
        # the caller passes an empty list.
        q = q.filter(EvalResult.ingestion_run_id.in_(list(ingestion_run_ids)))
    return q


def _row_to_run_summary(row) -> EvalRunSummary:
    total = int(row.total or 0)
    passes = int(row.pass_count or 0)
    partials = int(row.partial_count or 0)
    fails = int(row.fail_count or 0)
    hits = int(row.hit_count or 0)
    failed_status = int(row.failed_status_count or 0)
    summary = {
        "total": total,
        "pass": passes,
        "partial": partials,
        "fail": fails,
        "pass_rate": (passes / total) if total else 0.0,
        "partial_rate": (partials / total) if total else 0.0,
        "fail_rate": (fails / total) if total else 0.0,
        "retrieval_hit_rate": (hits / total) if total else 0.0,
        "avg_correctness": float(row.avg_correctness or 0.0),
        "avg_groundedness": float(row.avg_groundedness or 0.0),
        "avg_relevance": float(row.avg_relevance or 0.0),
        "total_questions": total,
        "duration_ms": int(row.duration_ms or 0),
    }
    for metric_name in _DEEPEVAL_SUMMARY_METRICS:
        summary[f"avg_{metric_name}"] = float(
            getattr(row, f"avg_{metric_name}", 0.0) or 0.0
        )
    status = "failed" if failed_status > 0 else "completed"
    return EvalRunSummary(
        run_id=row.run_id,
        upload_id=row.upload_id,
        ingestion_run_id=row.ingestion_run_id,
        run_number=int(row.run_number or 0),
        triggered_by=row.triggered_by,
        top_k=int(row.top_k or 0),
        answer_model=row.answer_model,
        judge_model=row.judge_model,
        status=status,
        error=None,
        started_at=row.started_at,
        completed_at=row.completed_at,
        summary=summary,
    )


def _result_row_to_dict(result: EvalResult, question: Eval) -> dict:
    return {
        "id": question.external_id,
        "eval_id": question.id,
        "category": question.category or "unknown",
        "question": question.question,
        "expected_answer": question.expected_answer,
        "expected_source_snippet": question.expected_source_snippet or "",
        "retrieval_hit": bool(result.retrieval_hit),
        "retrieved_chunks": result.retrieved_chunks or [],
        "actual_answer": result.actual_answer or "",
        "judge": {
            "verdict": result.verdict or "FAIL",
            "correctness": float(result.correctness or 0.0),
            "groundedness": float(result.groundedness or 0.0),
            "relevance": float(result.relevance or 0.0),
            "reasoning": result.judge_reasoning,
            "metric_scores": result.metric_scores or {},
        },
        "latency_ms": result.latency_ms,
        "retrieval_error": result.retrieval_error,
        "answer_error": result.answer_error,
        "status": result.status,
    }


def _diff_scored_rows(
    *,
    baseline_summary: EvalRunSummary,
    candidate_summary: EvalRunSummary,
    baseline_rows: List[dict],
    candidate_rows: List[dict],
    score_drop: float,
) -> dict:
    """Compare two runs' per-question rows. Output shape mirrors the
    pre-refactor helper so ``compare_runs.py`` needs no template changes."""
    b_rows = _index_by_id(baseline_rows)
    c_rows = _index_by_id(candidate_rows)
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

        # Per-DeepEval-metric deltas from the JSONB scorecard. Only emitted
        # when BOTH runs actually scored the metric — comparing a real
        # score to a missing/legacy row would coerce ``None → 0.0`` and
        # trigger a spurious "big drop" regression on every question.
        b_scores = (b["judge"].get("metric_scores") or {}) if isinstance(b["judge"], dict) else {}
        c_scores = (c["judge"].get("metric_scores") or {}) if isinstance(c["judge"], dict) else {}
        metric_deltas: dict[str, float] = {}
        for metric_name in _DEEPEVAL_SUMMARY_METRICS:
            b_entry = b_scores.get(metric_name)
            c_entry = c_scores.get(metric_name)
            b_raw = b_entry.get("score") if isinstance(b_entry, dict) else None
            c_raw = c_entry.get("score") if isinstance(c_entry, dict) else None
            if b_raw is None or c_raw is None:
                continue
            metric_deltas[metric_name] = _safe_score(c_raw) - _safe_score(b_raw)

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
        else:
            # A big drop on any DeepEval metric — even one not mapped to a
            # legacy column — is still a regression the compare view should
            # surface. Hallucination is inverted (higher = worse), so a
            # positive delta above the threshold is the regression signal.
            for metric_name, delta in metric_deltas.items():
                if metric_name in _INVERTED_SUMMARY_METRICS:
                    if delta >= score_drop:
                        note = f"{metric_name} rose {delta:+.2f}"
                        is_regression = True
                        break
                elif delta <= -score_drop:
                    note = f"{metric_name} drop {delta:+.2f}"
                    is_regression = True
                    break

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
        for metric_name, delta in metric_deltas.items():
            entry[f"delta_{metric_name}"] = delta
        per_question_diff.append(entry)
        if is_regression:
            regressions.append(entry)

    return {
        "baseline": {
            "id": str(baseline_summary.run_id),
            "run_number": baseline_summary.run_number,
            "started_at": baseline_summary.started_at.isoformat() if baseline_summary.started_at else None,
            "summary": baseline_summary.summary or {},
        },
        "candidate": {
            "id": str(candidate_summary.run_id),
            "run_number": candidate_summary.run_number,
            "started_at": candidate_summary.started_at.isoformat() if candidate_summary.started_at else None,
            "summary": candidate_summary.summary or {},
        },
        "score_drop_threshold": score_drop,
        "regressions": regressions,
        "regression_count": len(regressions),
        "per_question": per_question_diff,
    }


def _index_by_id(rows: List[dict]) -> dict:
    return {r["id"]: r for r in rows if isinstance(r, dict) and "id" in r}


def _safe_score(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

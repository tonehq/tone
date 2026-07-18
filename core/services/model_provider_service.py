"""Business logic for the Model Providers page (per-org ApiKey + per-provider
Model management). Shared by ``core/api/v1/services.py`` and
``ee/api/v1/services.py`` so the two editions cannot drift."""

from typing import Any, Iterable, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, distinct, func, or_
from sqlalchemy.orm import Session, joinedload

from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_language import ModelLanguage
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.services.base import BaseService
from core.services.crud import list_records
from core.utils.encryption import encrypt
from core.utils.faceted_query import apply_filters


ALLOWED_SERVICE_TYPES = {"llm", "stt", "tts"}
ALLOWED_MODEL_KINDS = {"llm", "stt", "tts"}
ALLOWED_KEY_SORT_FIELDS = {
    "label",
    "service_type",
    "is_default",
    "is_active",
    "created_at",
    "updated_at",
}
ALLOWED_MODEL_SORT_FIELDS = {"name", "kind", "is_active", "created_at", "updated_at"}
ALLOWED_USAGE_SORT_FIELDS = {"display_name", "api_key_count", "last_used_at"}
ALLOWED_PROVIDER_SORT_FIELDS = {
    "display_name",
    "slug",
    "provider_id",
    "is_active",
    "created_at",
    "updated_at",
}


# ─── module-level helpers (pure, no instance state) ─────────────────────────


def _parse_uuid(value: Any, *, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}"
        )


def _validate_service_type(value: Any, *, required: bool) -> str | None:
    if value is None or value == "":
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_type is required",
            )
        return None
    if value not in ALLOWED_SERVICE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"service_type must be one of {sorted(ALLOWED_SERVICE_TYPES)}",
        )
    return value


def _validate_model_kind(value: Any, *, required: bool) -> str | None:
    if value is None or value == "":
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="kind is required"
            )
        return None
    if value not in ALLOWED_MODEL_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"kind must be one of {sorted(ALLOWED_MODEL_KINDS)}",
        )
    return value


def _model_to_dict(m: Model) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "display_name": m.display_name,
        "kind": m.kind,
        "description": m.description,
        "base_url": m.base_url,
        "is_active": bool(m.is_active),
        "meta_data": m.meta_data,
        "meta_data_schema": m.meta_data_schema,
        "created_at": int(m.created_at.timestamp()) if m.created_at else None,
        "updated_at": int(m.updated_at.timestamp()) if m.updated_at else None,
    }


def _optional_str(body: dict, key: str) -> Optional[str]:
    """Trim a request-body string and return ``None`` for empty/missing values.
    Centralises the ``(x or "").strip() or None`` pattern used across model writes."""
    return (body.get(key) or "").strip() or None


# ─── service class ──────────────────────────────────────────────────────────


class ModelProviderService(BaseService):
    """All business logic for the Model Providers page. Routes are thin wrappers."""

    # ─── shared lookup helpers ──────────────────────────────────────────────

    def _provider_kinds_map(
        self, provider_ids: Iterable[UUID]
    ) -> dict[str, list[str]]:
        """Single batched query → dict[provider_id_str, list[kind]]. Avoids N+1."""
        ids = list(provider_ids)
        if not ids:
            return {}
        rows = (
            self.db.query(Model.provider_id, Model.kind)
            .filter(Model.provider_id.in_(ids), Model.is_active.is_(True))
            .distinct()
            .all()
        )
        out: dict[str, list[str]] = {}
        for provider_id, kind in rows:
            out.setdefault(str(provider_id), []).append(kind)
        for k in out:
            out[k].sort()
        return out

    def _model_count_by_provider_kind_map(
        self, provider_ids: Iterable[UUID]
    ) -> dict[tuple[str, str], int]:
        """{(provider_id_str, kind): count} for active models. Lets the
        listing show kind-scoped model counts when each card represents
        one (provider, service_type) pair."""
        ids = list(provider_ids)
        if not ids:
            return {}
        rows = (
            self.db.query(Model.provider_id, Model.kind, func.count(Model.id))
            .filter(Model.provider_id.in_(ids), Model.is_active.is_(True))
            .group_by(Model.provider_id, Model.kind)
            .all()
        )
        return {(str(pid), kind): int(count) for pid, kind, count in rows}

    def _default_keys_by_provider_kind_map(
        self, provider_ids: Iterable[UUID]
    ) -> dict[tuple[str, str], dict]:
        """{(provider_id_str, service_type): default_key_dict}. The partial
        unique index guarantees at most one default per (org, service_type)."""
        ids = list(provider_ids)
        if not ids:
            return {}
        rows = (
            self.db.query(
                ApiKey.id, ApiKey.label, ApiKey.service_type, ApiKey.provider_id
            )
            .filter(
                ApiKey.organization_id == self.org_id,
                ApiKey.provider_id.in_(ids),
                ApiKey.is_default.is_(True),
            )
            .all()
        )
        out: dict[tuple[str, str], dict] = {}
        for row in rows:
            out[(str(row.provider_id), row.service_type)] = {
                "id": str(row.id),
                "label": row.label,
                "service_type": row.service_type,
            }
        return out

    def _provider_or_404(self, provider_id: UUID) -> ModelProvider:
        provider = (
            self.db.query(ModelProvider)
            .filter(ModelProvider.id == provider_id)
            .first()
        )
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
            )
        return provider

    def _model_or_404(self, *, provider_id: UUID, model_id: UUID) -> Model:
        record = (
            self.db.query(Model)
            .filter(Model.id == model_id, Model.provider_id == provider_id)
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Model not found"
            )
        return record

    def _flip_other_defaults(
        self, *, service_type: str | None, keep_id: UUID | None
    ) -> None:
        if not service_type:
            return
        q = self.db.query(ApiKey).filter(
            ApiKey.organization_id == self.org_id,
            ApiKey.service_type == service_type,
            ApiKey.is_default.is_(True),
        )
        if keep_id is not None:
            q = q.filter(ApiKey.id != keep_id)
        q.update({ApiKey.is_default: False}, synchronize_session=False)

    def _assert_label_unique(
        self,
        *,
        provider_id: UUID,
        label: str | None,
        exclude_id: UUID | None = None,
    ) -> None:
        """Pre-check the partial unique constraint ``uq_api_keys_org_provider_label``
        so a duplicate label returns a clean 409 instead of bubbling up as a
        500 IntegrityError from the DB layer. NULL labels are not constrained
        (Postgres treats NULLs as distinct), matching the index semantics."""
        if not label:
            return
        q = self.db.query(ApiKey.id).filter(
            ApiKey.organization_id == self.org_id,
            ApiKey.provider_id == provider_id,
            ApiKey.label == label,
        )
        if exclude_id is not None:
            q = q.filter(ApiKey.id != exclude_id)
        if q.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An API key with this label already exists for the provider.",
            )

    def _service_record(self, service_id: UUID) -> ApiKey:
        record = (
            self.db.query(ApiKey)
            .options(joinedload(ApiKey.provider))
            .filter(
                ApiKey.id == service_id, ApiKey.organization_id == self.org_id
            )
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )
        return record

    # ─── faceted list helpers ──────────────────────────────────────────────

    # Faceted (drawer) fields for the aggregated usage list. ``name`` is a
    # token-bar-only multi-select (provider display name); ``service_type`` is
    # the drawer facet.
    USAGE_FACET_FIELDS = ["service_type"]

    def _usage_base_query(self):
        """Org-scoped base for the usage list — one ApiKey row per key, joined to
        its provider, excluding legacy NULL service_type rows."""
        return (
            self.db.query(ApiKey)
            .join(ModelProvider, ModelProvider.id == ApiKey.provider_id)
            .filter(
                ApiKey.organization_id == self.org_id,
                ApiKey.service_type.isnot(None),
            )
        )

    def _usage_column_map(self) -> dict:
        return {
            "service_type": ApiKey.service_type,
            "name": ModelProvider.display_name,
            "status": case((ApiKey.is_active.is_(True), "active"), else_="inactive"),
        }

    def get_service_facets(self, filters: list | None = None) -> dict:
        """Per-value facet counts for the Model Providers filter drawer. Counts
        are by distinct (provider, service_type) card, not raw ApiKey rows."""
        column_map = self._usage_column_map()
        result: dict = {}
        for field in self.USAGE_FACET_FIELDS:
            col = column_map.get(field)
            if col is None:
                continue
            scoped = apply_filters(
                self._usage_base_query(), filters, column_map, exclude_field=field
            )
            rows = (
                scoped.with_entities(col, func.count(distinct(ApiKey.provider_id)))
                .group_by(col)
                .all()
            )
            result[field] = [{"value": v, "count": int(c)} for v, c in rows if v]
        return result

    def get_service_filter_values(self, column_name: str) -> dict:
        """Distinct values for token-search autocomplete.

        ``service_type`` stays scoped to the org's ApiKeys — an unconfigured
        kind has nothing to filter to. ``name`` returns every active provider
        in the catalog so the Model Providers page can search unconnected
        providers too (the listing renders them via ``include_unconnected``)."""
        if column_name == "service_type":
            base = self._usage_base_query()
            rows = base.with_entities(ApiKey.service_type).distinct().all()
        elif column_name == "name":
            rows = (
                self.db.query(ModelProvider.display_name)
                .filter(ModelProvider.is_active.is_(True))
                .distinct()
                .all()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid column: {column_name}. Allowed: name, service_type",
            )
        values = sorted([r[0] for r in rows if r[0]])
        return {"column": column_name, "values": values}

    # ─── list / aggregate ──────────────────────────────────────────────────

    def list_services(self, body: dict) -> dict:
        """Aggregated list — one row per distinct (provider, service_type)
        the org has ≥1 ApiKey for. A Deepgram STT key and a Deepgram TTS key
        therefore surface as two separate cards on the listing page.

        When ``include_unconnected`` is true, providers the org has NO ApiKey
        for are appended as extra rows with ``service_type=None`` and zeroed
        counts — used by the Model Providers page which surfaces the full
        catalog (agent-form dropdowns still call the connection-scoped
        endpoints and stay filtered to configured providers)."""
        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 12), 1), 100)
        search = body.get("search")
        sort_by = body.get("sort_by")
        service_type = body.get("service_type")
        status_filter = body.get("status")
        include_unconnected = bool(body.get("include_unconnected", False))

        api_key_count = func.count(ApiKey.id).label("api_key_count")
        active_api_key_count = func.count(
            case((ApiKey.is_active.is_(True), ApiKey.id))
        ).label("active_api_key_count")
        last_used_at = func.max(ApiKey.updated_at).label("last_used_at")

        q = (
            self.db.query(
                ApiKey.provider_id.label("provider_id"),
                ApiKey.service_type.label("service_type"),
                ModelProvider.slug,
                ModelProvider.display_name,
                ModelProvider.description,
                api_key_count,
                active_api_key_count,
                last_used_at,
            )
            .join(ModelProvider, ModelProvider.id == ApiKey.provider_id)
            .filter(
                ApiKey.organization_id == self.org_id,
                # Each card represents one (provider, service_type) pair, so
                # legacy rows with NULL service_type can't be rendered or
                # deleted from the listing — exclude them rather than surface
                # broken cards with empty badges and 400-ing delete CTAs.
                ApiKey.service_type.isnot(None),
            )
        )

        if search:
            like = f"%{search}%"
            q = q.filter(
                (ModelProvider.display_name.ilike(like))
                | (ApiKey.label.ilike(like))
            )
        if service_type and service_type != "all":
            _validate_service_type(service_type, required=False)
            q = q.filter(ApiKey.service_type == service_type)
        if status_filter == "active":
            q = q.filter(ApiKey.is_active.is_(True))
        elif status_filter == "inactive":
            q = q.filter(ApiKey.is_active.is_(False))

        # Generic faceted filters (token bar Name multi-select + Type facet).
        generic_filters = body.get("filters")
        if generic_filters:
            q = apply_filters(q, generic_filters, self._usage_column_map())

        q = q.group_by(
            ApiKey.provider_id,
            ApiKey.service_type,
            ModelProvider.slug,
            ModelProvider.display_name,
            ModelProvider.description,
            ModelProvider.id,
        )

        total = self.db.query(func.count()).select_from(q.subquery()).scalar() or 0

        sort_map = {
            "display_name": ModelProvider.display_name,
            "api_key_count": api_key_count,
            "last_used_at": last_used_at,
        }
        order_col = last_used_at
        desc_dir = True
        if sort_by:
            d = sort_by.startswith("-")
            f = sort_by.lstrip("-")
            if f in ALLOWED_USAGE_SORT_FIELDS:
                order_col = sort_map[f]
                desc_dir = d
        # Stable tiebreak so STT/TTS rows for the same provider stay
        # adjacent and in a consistent order across requests.
        q = q.order_by(
            order_col.desc() if desc_dir else order_col.asc(),
            ModelProvider.display_name.asc(),
            ApiKey.service_type.asc(),
        )

        # Fetch strategy: when ``include_unconnected`` is false we keep the
        # SQL-side pagination (unchanged behavior for every existing caller).
        # When true we fetch the full connected list, union unconnected
        # providers in Python, and paginate the combined result. The catalog
        # is small (≤ a few hundred providers) so this is cheap and much
        # simpler than a SQL-level UNION with correct pagination.
        if include_unconnected:
            connected_rows = q.all()
        else:
            connected_rows = q.offset((page - 1) * page_size).limit(page_size).all()

        # Providers the org has NO ApiKey against — only queried when
        # ``include_unconnected`` is true AND no filter narrows the result to
        # a specific service_type or key status (those filters don't apply to
        # "not yet connected" cards, so we'd risk showing them under a filter
        # they can't satisfy).
        unconnected_providers: list[ModelProvider] = []
        can_include_unconnected = (
            include_unconnected
            and (not service_type or service_type == "all")
            and status_filter not in ("active", "inactive")
        )
        if can_include_unconnected:
            connected_ids_subq = self.db.query(distinct(ApiKey.provider_id)).filter(
                ApiKey.organization_id == self.org_id,
                ApiKey.service_type.isnot(None),
            )
            uq = self.db.query(ModelProvider).filter(
                ModelProvider.is_active.is_(True),
                ~ModelProvider.id.in_(connected_ids_subq),
            )
            if search:
                like = f"%{search}%"
                uq = uq.filter(
                    (ModelProvider.display_name.ilike(like))
                    | (ModelProvider.slug.ilike(like))
                )
            # Only the "name" facet applies here — a service_type facet
            # would exclude unconnected rows by definition.
            if generic_filters:
                name_only = [
                    f for f in generic_filters if f.get("field") == "name"
                ]
                if name_only:
                    uq = apply_filters(uq, name_only, self._usage_column_map())
            unconnected_providers = uq.order_by(
                ModelProvider.display_name.asc()
            ).all()

        # Combine and paginate when we're serving the unified list. Otherwise
        # the SQL LIMIT above already gave us the right page.
        if include_unconnected:
            total = len(connected_rows) + len(unconnected_providers)
            start = (page - 1) * page_size
            end = start + page_size
            connected_slice = connected_rows[start:end]
            remaining = page_size - len(connected_slice)
            unconnected_start = max(0, start - len(connected_rows))
            unconnected_slice = (
                unconnected_providers[
                    unconnected_start : unconnected_start + remaining
                ]
                if remaining > 0
                else []
            )
        else:
            connected_slice = connected_rows
            unconnected_slice = []

        provider_ids = [r.provider_id for r in connected_slice if r.provider_id]
        provider_ids.extend(p.id for p in unconnected_slice)
        model_count_map = self._model_count_by_provider_kind_map(provider_ids)
        default_map = self._default_keys_by_provider_kind_map(provider_ids)

        # Batch-fetch meta_data_schema for all providers in this page
        provider_schema_map = {}
        if provider_ids:
            schema_rows = (
                self.db.query(ModelProvider.id, ModelProvider.meta_data_schema)
                .filter(ModelProvider.id.in_(provider_ids))
                .all()
            )
            provider_schema_map = {str(r.id): r.meta_data_schema for r in schema_rows}

        def _row_to_dict(r) -> dict:
            pid = str(r.provider_id)
            kind = r.service_type
            schema = provider_schema_map.get(pid)
            return {
                "id": f"{pid}:{kind}",
                "provider": {
                    "id": pid,
                    "slug": r.slug,
                    "display_name": r.display_name,
                    "description": r.description,
                },
                "service_type": kind,
                "api_key_count": int(r.api_key_count or 0),
                "active_api_key_count": int(r.active_api_key_count or 0),
                "default_api_key": default_map.get((pid, kind)),
                "model_count": model_count_map.get((pid, kind), 0),
                "last_used_at": (
                    int(r.last_used_at.timestamp()) if r.last_used_at else None
                ),
                "meta_data_schema": (
                    schema.get(kind) if isinstance(schema, dict) else None
                ),
            }

        def _unconnected_to_dict(p: ModelProvider) -> dict:
            pid = str(p.id)
            return {
                "id": f"{pid}:none",
                "provider": {
                    "id": pid,
                    "slug": p.slug,
                    "display_name": p.display_name,
                    "description": p.description,
                },
                "service_type": None,
                "api_key_count": 0,
                "active_api_key_count": 0,
                "default_api_key": None,
                "model_count": 0,
                "last_used_at": None,
                "meta_data_schema": None,
            }

        items = [_row_to_dict(r) for r in connected_slice]
        items.extend(_unconnected_to_dict(p) for p in unconnected_slice)

        return {
            "items": items,
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }

    # ─── single-key CRUD ───────────────────────────────────────────────────

    def create_service(self, body: dict) -> dict:
        provider_id = _parse_uuid(body.get("provider_id"), field="provider_id")
        self._provider_or_404(provider_id)

        service_type = _validate_service_type(
            body.get("service_type"), required=True
        )

        api_key_value = (body.get("api_key") or "").strip()
        source_key_id = body.get("source_key_id")

        # Exactly one of api_key / source_key_id must be provided. When
        # source_key_id is given, copy the encrypted_key from an existing key
        # on the same provider so the user doesn't have to paste the secret
        # again when adding a second service (e.g. Deepgram STT → TTS).
        if api_key_value and source_key_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either api_key or source_key_id, not both",
            )
        if not api_key_value and not source_key_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="api_key or source_key_id is required",
            )

        if source_key_id:
            src_uuid = _parse_uuid(source_key_id, field="source_key_id")
            source = (
                self.db.query(ApiKey)
                .filter(
                    ApiKey.id == src_uuid,
                    ApiKey.organization_id == self.org_id,
                )
                .first()
            )
            if not source:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Source API key not found",
                )
            if source.provider_id != provider_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_key_id must belong to the same provider",
                )
            encrypted_key = source.encrypted_key
        else:
            encrypted_key = encrypt(api_key_value)

        label = (body.get("label") or "").strip() or None
        description = (body.get("description") or "").strip() or None
        is_default = bool(body.get("is_default", False))
        is_active = bool(body.get("is_active", True))
        config = body.get("config") or {}
        if not isinstance(config, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="config must be a JSON object",
            )

        self._assert_label_unique(provider_id=provider_id, label=label)

        if is_default:
            self._flip_other_defaults(service_type=service_type, keep_id=None)

        record = ApiKey(
            organization_id=self.org_id,
            provider_id=provider_id,
            label=label,
            encrypted_key=encrypted_key,
            is_active=is_active,
            service_type=service_type,
            description=description,
            is_default=is_default,
            config=config,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        kinds = self._provider_kinds_map([record.provider_id]).get(
            str(record.provider_id), []
        )
        return record.to_dict(kinds=kinds)

    def get_service(self, service_id: str) -> dict:
        svc_uuid = _parse_uuid(service_id, field="service id")
        record = self._service_record(svc_uuid)
        kinds = self._provider_kinds_map([record.provider_id]).get(
            str(record.provider_id), []
        )
        return record.to_dict(kinds=kinds)

    def update_service(self, service_id: str, body: dict) -> dict:
        svc_uuid = _parse_uuid(service_id, field="service id")
        record = self._service_record(svc_uuid)

        # 1. Resolve the post-patch values for the two interlocking fields
        #    (service_type and is_default). The partial unique index
        #    ``uq_api_keys_one_default_per_org_type`` requires only one
        #    is_default=true row per (org, service_type), so we have to reason
        #    about the *combined* end state, not field-by-field.
        will_be_default = (
            bool(body["is_default"]) if "is_default" in body else record.is_default
        )

        service_type_changing = False
        new_service_type: str | None = record.service_type
        if "service_type" in body:
            new_service_type = _validate_service_type(
                body.get("service_type"), required=False
            )
            service_type_changing = new_service_type != record.service_type
            # A default key with no service_type would bypass the partial
            # unique index (NULLs aren't constrained) and would leave the row
            # in a logically inconsistent state. Force the caller to disclaim
            # default-ness in the same request.
            if will_be_default and new_service_type is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "service_type cannot be cleared while is_default is true; "
                        "set is_default=false in the same request"
                    ),
                )

        # 2. Apply field updates. provider_id is NOT NULL in the schema, so
        #    we require a truthy value if it's present in the body — and we
        #    reject an explicit null with a 400 to match the other validated
        #    fields, rather than silently ignoring it.
        if "provider_id" in body:
            if not body["provider_id"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="provider_id cannot be null",
                )
            new_provider_id = _parse_uuid(body["provider_id"], field="provider_id")
            self._provider_or_404(new_provider_id)
            record.provider_id = new_provider_id

        if "service_type" in body:
            record.service_type = new_service_type

        if "label" in body:
            record.label = (body.get("label") or "").strip() or None

        # Re-check label uniqueness after both provider_id and label have been
        # applied — either change alone can collide with an existing row under
        # uq_api_keys_org_provider_label.
        if "provider_id" in body or "label" in body:
            self._assert_label_unique(
                provider_id=record.provider_id,
                label=record.label,
                exclude_id=record.id,
            )
        if "description" in body:
            v = (body.get("description") or "").strip()
            record.description = v or None
        if "is_active" in body:
            record.is_active = bool(body["is_active"])
        if "config" in body:
            config = body.get("config") or {}
            if not isinstance(config, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="config must be a JSON object",
                )
            record.config = config
        if "api_key" in body and body["api_key"]:
            new_key = str(body["api_key"]).strip()
            if new_key:
                record.encrypted_key = encrypt(new_key)

        # 3. Flip other defaults whenever the record will end up as the new
        #    default for its (possibly new) service_type. Two cases:
        #      (a) is_default was just toggled to True (explicit set).
        #      (b) record was already default AND service_type is moving —
        #          without this branch the commit fails with an IntegrityError
        #          from the partial unique index.
        explicit_default_set = "is_default" in body and bool(body["is_default"])
        carrying_default_to_new_type = (
            record.is_default and service_type_changing and will_be_default
        )
        if will_be_default and new_service_type and (
            explicit_default_set or carrying_default_to_new_type
        ):
            self._flip_other_defaults(
                service_type=new_service_type, keep_id=record.id
            )

        if "is_default" in body:
            record.is_default = will_be_default

        self.db.commit()
        self.db.refresh(record)
        kinds = self._provider_kinds_map([record.provider_id]).get(
            str(record.provider_id), []
        )
        return record.to_dict(kinds=kinds)

    def delete_service(self, service_id: str) -> dict:
        svc_uuid = _parse_uuid(service_id, field="service id")
        record = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == svc_uuid, ApiKey.organization_id == self.org_id)
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
            )
        self.db.delete(record)
        self.db.commit()
        return {"ok": True}

    def delete_provider_services(
        self, provider_id: str, service_type: str | None = None
    ) -> dict:
        """Delete all of the org's API keys for the provider, or just those of
        a single ``service_type`` when the listing's card is per-(provider,
        kind) and the user only wants to remove that card."""
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)

        validated_kind = _validate_service_type(service_type, required=False)

        q = self.db.query(ApiKey).filter(
            ApiKey.organization_id == self.org_id,
            ApiKey.provider_id == prov_uuid,
        )
        if validated_kind:
            q = q.filter(ApiKey.service_type == validated_kind)
        deleted = q.delete(synchronize_session=False)
        self.db.commit()
        return {"deleted": int(deleted)}

    # ─── catalog ───────────────────────────────────────────────────────────

    def list_providers_catalog(self, service_type: str | None = None) -> list[dict]:
        service_type = _validate_service_type(service_type, required=False)

        q = self.db.query(ModelProvider)

        providers = q.order_by(ModelProvider.display_name.asc()).all()
        kinds_map = self._provider_kinds_map([p.id for p in providers])
        return [
            {
                "id": str(p.id),
                "slug": p.slug,
                "display_name": p.display_name,
                "description": p.description,
                # When scoped to a single kind, returning only that kind avoids
                # leaking provider capabilities the caller didn't ask about.
                "kinds": [service_type] if service_type else kinds_map.get(str(p.id), []),
                "meta_data_schema": p.meta_data_schema,
            }
            for p in providers
        ]

    # ─── per-provider drill-down ───────────────────────────────────────────

    def list_provider_keys(self, provider_id: str, body: dict) -> dict:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)

        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 20), 1), 100)
        search = body.get("search")
        sort_by = body.get("sort_by")
        service_type = body.get("service_type")
        status_filter = body.get("status")

        filters = [ApiKey.provider_id == prov_uuid]
        if search:
            filters.append(ApiKey.label.ilike(f"%{search}%"))
        if service_type and service_type != "all":
            _validate_service_type(service_type, required=False)
            filters.append(ApiKey.service_type == service_type)
        if status_filter == "active":
            filters.append(ApiKey.is_active.is_(True))
        elif status_filter == "inactive":
            filters.append(ApiKey.is_active.is_(False))

        order_by = ApiKey.updated_at.desc()
        if sort_by:
            d = sort_by.startswith("-")
            f = sort_by.lstrip("-")
            if f in ALLOWED_KEY_SORT_FIELDS:
                col = getattr(ApiKey, f)
                order_by = col.desc() if d else col.asc()

        items, total = list_records(
            self.db,
            ApiKey,
            self.org_id,
            page,
            page_size,
            filters,
            order_by,
            options=[joinedload(ApiKey.provider)],
        )

        kinds = self._provider_kinds_map([prov_uuid]).get(str(prov_uuid), [])
        return {
            "items": [i.to_dict(kinds=kinds) for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_provider_models(self, provider_id: str, body: dict) -> dict:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)

        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 50), 1), 200)
        search = body.get("search")
        sort_by = body.get("sort_by")
        service_type = _validate_service_type(
            body.get("service_type"), required=False
        )

        q = self.db.query(Model).filter(Model.provider_id == prov_uuid)

        if service_type:
            q = q.filter(Model.kind == service_type)

        if search:
            q = q.filter(Model.name.ilike(f"%{search}%"))

        total = q.count()

        order_by = Model.name.asc()
        if sort_by:
            d = sort_by.startswith("-")
            f = sort_by.lstrip("-")
            if f in ALLOWED_MODEL_SORT_FIELDS:
                col = getattr(Model, f)
                order_by = col.desc() if d else col.asc()
        q = q.order_by(order_by)

        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [_model_to_dict(m) for m in rows],
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }

    def get_provider_key_filter_values(
        self, provider_id: str, column_name: str, service_type: str | None = None
    ) -> dict:
        """Distinct API-key names (labels) for token-search autocomplete."""
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)
        if column_name not in ("name", "label"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid column: {column_name}. Allowed: name",
            )
        q = self.db.query(ApiKey.label).filter(
            ApiKey.organization_id == self.org_id,
            ApiKey.provider_id == prov_uuid,
        )
        if service_type and service_type != "all":
            _validate_service_type(service_type, required=False)
            q = q.filter(ApiKey.service_type == service_type)
        values = sorted([r[0] for r in q.distinct().all() if r[0]])
        return {"column": column_name, "values": values}

    def get_provider_model_filter_values(
        self, provider_id: str, column_name: str, service_type: str | None = None
    ) -> dict:
        """Distinct model names for token-search autocomplete."""
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)
        if column_name != "name":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid column: {column_name}. Allowed: name",
            )
        q = self.db.query(Model.name).filter(Model.provider_id == prov_uuid)
        service_type = _validate_service_type(service_type, required=False)
        if service_type:
            q = q.filter(Model.kind == service_type)
        values = sorted([r[0] for r in q.distinct().all() if r[0]])
        return {"column": column_name, "values": values}

    # ─── model CRUD ────────────────────────────────────────────────────────

    def create_provider_model(self, provider_id: str, body: dict) -> dict:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)

        name = (body.get("name") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="name is required"
            )
        kind = _validate_model_kind(body.get("kind"), required=True)

        exists = (
            self.db.query(Model.id)
            .filter(Model.provider_id == prov_uuid, Model.name == name)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A model with this name already exists for the provider.",
            )

        record = Model(
            provider_id=prov_uuid,
            name=name,
            display_name=_optional_str(body, "display_name"),
            kind=kind,
            description=_optional_str(body, "description"),
            base_url=_optional_str(body, "base_url"),
            is_active=bool(body.get("is_active", True)),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return _model_to_dict(record)

    def update_provider_model(
        self, provider_id: str, model_id: str, body: dict
    ) -> dict:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        m_uuid = _parse_uuid(model_id, field="model id")
        self._provider_or_404(prov_uuid)
        record = self._model_or_404(provider_id=prov_uuid, model_id=m_uuid)

        if "name" in body:
            new_name = (body.get("name") or "").strip()
            if not new_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="name cannot be empty",
                )
            if new_name != record.name:
                clash = (
                    self.db.query(Model.id)
                    .filter(
                        Model.provider_id == prov_uuid,
                        Model.name == new_name,
                        Model.id != record.id,
                    )
                    .first()
                )
                if clash:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A model with this name already exists for the provider.",
                    )
            record.name = new_name
        if "display_name" in body:
            record.display_name = _optional_str(body, "display_name")
        if "kind" in body:
            record.kind = (
                _validate_model_kind(body.get("kind"), required=False) or record.kind
            )
        if "description" in body:
            record.description = _optional_str(body, "description")
        if "base_url" in body:
            record.base_url = _optional_str(body, "base_url")
        if "is_active" in body:
            record.is_active = bool(body["is_active"])

        self.db.commit()
        self.db.refresh(record)
        return _model_to_dict(record)

    def delete_provider_model(self, provider_id: str, model_id: str) -> dict:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        m_uuid = _parse_uuid(model_id, field="model id")
        self._provider_or_404(prov_uuid)
        record = self._model_or_404(provider_id=prov_uuid, model_id=m_uuid)
        self.db.delete(record)
        self.db.commit()
        return {"ok": True}

    # ─── TTS cascade (language → provider → voice) ────────────────────────

    def list_tts_languages(self) -> List[dict]:
        """Return distinct languages available across all active TTS models.

        Groups by ``display_name`` so the UI dropdown is deduplicated.
        Returns the canonical display name and all provider-specific codes
        that map to it, so the frontend can resolve saved codes on edit.
        """
        rows = (
            self.db.query(
                ModelLanguage.display_name,
                func.array_agg(distinct(ModelLanguage.name)),
            )
            .join(Model, Model.id == ModelLanguage.model_id)
            .filter(
                Model.kind == "tts",
                Model.is_active.is_(True),
                ModelLanguage.is_active.is_(True),
                ModelLanguage.display_name.isnot(None),
            )
            .group_by(ModelLanguage.display_name)
            .order_by(ModelLanguage.display_name.asc())
            .all()
        )
        return [{"name": row[0], "codes": sorted(row[1])} for row in rows]

    def list_tts_providers(self, language: str) -> List[dict]:
        """Return TTS providers that have models supporting the given language.

        ``language`` is a display name (e.g. "English").  For each provider the
        response includes the first matching provider-specific code so the
        frontend can persist it in ``voice_settings.language_code``.
        """
        rows = (
            self.db.query(
                ModelProvider,
                func.min(ModelLanguage.name),  # first provider-specific code
            )
            .join(Model, Model.provider_id == ModelProvider.id)
            .join(ModelLanguage, ModelLanguage.model_id == Model.id)
            .filter(
                Model.kind == "tts",
                Model.is_active.is_(True),
                ModelProvider.is_active.is_(True),
                ModelLanguage.is_active.is_(True),
                ModelLanguage.display_name == language,
            )
            .group_by(ModelProvider.id)
            .order_by(ModelProvider.display_name.asc())
            .all()
        )
        return [
            {
                "id": str(p.id),
                "slug": p.slug,
                "display_name": p.display_name,
                "description": p.description,
                "language_code": code,
                "meta_data_schema": (
                    p.meta_data_schema.get("tts")
                    if isinstance(p.meta_data_schema, dict)
                    else None
                ),
            }
            for p, code in rows
        ]

    def list_tts_voices(self, provider_id: str, language: str, model_id: str = None) -> List[dict]:
        """Return TTS voices for a provider that support the given language.

        ``language`` is a display name (e.g. "English").  The method resolves
        it to all matching provider-specific codes and filters voices whose
        ``language_list`` JSONB array contains any of those codes.

        If ``model_id`` is provided, only voices belonging to that model are returned.
        """
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        self._provider_or_404(prov_uuid)

        # Resolve display name → provider-specific codes for this provider
        code_rows = (
            self.db.query(ModelLanguage.name)
            .join(Model, Model.id == ModelLanguage.model_id)
            .filter(
                Model.provider_id == prov_uuid,
                Model.kind == "tts",
                ModelLanguage.is_active.is_(True),
                ModelLanguage.display_name == language,
            )
            .distinct()
            .all()
        )
        codes = [r[0] for r in code_rows]

        if not codes:
            # Fallback: treat language as a raw code (backward compat)
            codes = [language]

        query = (
            self.db.query(ModelVoice)
            .join(Model, Model.id == ModelVoice.model_id)
            .filter(
                Model.provider_id == prov_uuid,
                Model.kind == "tts",
                Model.is_active.is_(True),
                ModelVoice.is_active.is_(True),
                or_(*(ModelVoice.language_list.contains([c]) for c in codes)),
            )
        )

        if model_id:
            model_uuid = _parse_uuid(model_id, field="model id")
            query = query.filter(Model.id == model_uuid)

        rows = query.order_by(ModelVoice.name.asc()).all()
        return [
            {
                "id": str(v.id),
                "name": v.name,
                "gender": v.gender,
                "accent": v.accent,
                "description": v.description,
                "language_list": v.language_list,
                "sample_url": v.sample_url,
            }
            for v in rows
        ]

    # ─── provider CRUD (admin) ─────────────────────────────────────────────

    def provider_response(self, provider: ModelProvider) -> dict:
        """Public formatter for a ModelProvider row — used by the admin
        create/update/list endpoints so responses stay in one place."""
        return {
            "id": str(provider.id),
            "provider_id": provider.provider_id,
            "slug": provider.slug,
            "display_name": provider.display_name,
            "description": provider.description,
            "website_url": provider.website_url,
            "is_active": bool(provider.is_active),
            "meta_data_schema": provider.meta_data_schema,
            "created_at": (
                int(provider.created_at.timestamp()) if provider.created_at else None
            ),
            "updated_at": (
                int(provider.updated_at.timestamp()) if provider.updated_at else None
            ),
        }

    def _assert_provider_unique(
        self,
        *,
        provider_id: str | None = None,
        slug: str | None = None,
        exclude_id: UUID | None = None,
    ) -> None:
        """Pre-check the provider_id and slug uniqueness so duplicates return
        a clean 409 instead of a 500 IntegrityError from Postgres."""
        for field, value in (("provider_id", provider_id), ("slug", slug)):
            if not value:
                continue
            q = self.db.query(ModelProvider.id).filter(
                getattr(ModelProvider, field) == value
            )
            if exclude_id is not None:
                q = q.filter(ModelProvider.id != exclude_id)
            if q.first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A provider with this {field} already exists.",
                )

    def list_providers(self, body: dict) -> dict:
        """Admin listing of every ModelProvider in the catalog. Unlike
        ``list_providers_catalog`` this ignores org scope and returns inactive
        rows too so admins can manage them."""
        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 20), 1), 100)
        search = (body.get("search") or "").strip()
        sort_by = body.get("sort_by")
        is_active = body.get("is_active")

        q = self.db.query(ModelProvider)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    ModelProvider.display_name.ilike(like),
                    ModelProvider.slug.ilike(like),
                    ModelProvider.provider_id.ilike(like),
                )
            )
        if is_active is True or is_active is False:
            q = q.filter(ModelProvider.is_active.is_(bool(is_active)))

        total = q.count()

        order_by = ModelProvider.display_name.asc()
        if sort_by:
            d = sort_by.startswith("-")
            f = sort_by.lstrip("-")
            if f in ALLOWED_PROVIDER_SORT_FIELDS:
                col = getattr(ModelProvider, f)
                order_by = col.desc() if d else col.asc()
        q = q.order_by(order_by)

        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [self.provider_response(p) for p in rows],
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }

    def get_provider(self, provider_id: str) -> ModelProvider:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        return self._provider_or_404(prov_uuid)

    def create_provider(self, body: dict) -> ModelProvider:
        provider_id_str = (body.get("provider_id") or "").strip()
        slug = (body.get("slug") or "").strip()
        display_name = (body.get("display_name") or "").strip()
        if not provider_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider_id is required",
            )
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="slug is required"
            )
        if not display_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="display_name is required",
            )

        meta_data_schema = body.get("meta_data_schema")
        if meta_data_schema is not None and not isinstance(meta_data_schema, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meta_data_schema must be a JSON object",
            )

        self._assert_provider_unique(provider_id=provider_id_str, slug=slug)

        record = ModelProvider(
            provider_id=provider_id_str,
            slug=slug,
            display_name=display_name,
            description=_optional_str(body, "description"),
            website_url=_optional_str(body, "website_url"),
            is_active=bool(body.get("is_active", True)),
            meta_data_schema=meta_data_schema,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_provider(self, provider_id: str, body: dict) -> ModelProvider:
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        record = self._provider_or_404(prov_uuid)

        new_provider_id: str | None = None
        new_slug: str | None = None

        if "provider_id" in body:
            candidate = (body.get("provider_id") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="provider_id cannot be empty",
                )
            if candidate != record.provider_id:
                new_provider_id = candidate

        if "slug" in body:
            candidate = (body.get("slug") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="slug cannot be empty",
                )
            if candidate != record.slug:
                new_slug = candidate

        if new_provider_id or new_slug:
            self._assert_provider_unique(
                provider_id=new_provider_id,
                slug=new_slug,
                exclude_id=record.id,
            )

        if new_provider_id:
            record.provider_id = new_provider_id
        if new_slug:
            record.slug = new_slug

        if "display_name" in body:
            candidate = (body.get("display_name") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="display_name cannot be empty",
                )
            record.display_name = candidate
        if "description" in body:
            record.description = _optional_str(body, "description")
        if "website_url" in body:
            record.website_url = _optional_str(body, "website_url")
        if "is_active" in body:
            record.is_active = bool(body["is_active"])
        if "meta_data_schema" in body:
            value = body.get("meta_data_schema")
            if value is not None and not isinstance(value, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="meta_data_schema must be a JSON object",
                )
            record.meta_data_schema = value

        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_provider(self, provider_id: str) -> dict:
        """Hard-delete a ModelProvider. Blocks the delete if any org has an
        ApiKey against this provider — deleting would orphan those credentials
        and silently break the agents that depend on them."""
        prov_uuid = _parse_uuid(provider_id, field="provider id")
        record = self._provider_or_404(prov_uuid)

        in_use = (
            self.db.query(ApiKey.id).filter(ApiKey.provider_id == prov_uuid).first()
        )
        if in_use:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot delete provider: one or more organizations have API "
                    "keys configured for it. Remove those keys first."
                ),
            )

        self.db.delete(record)
        self.db.commit()
        return {"ok": True}

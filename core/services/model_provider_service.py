"""Business logic for the Model Providers page (per-org ApiKey + per-provider
Model management). Shared by ``core/api/v1/services.py`` and
``ee/api/v1/services.py`` so the two editions cannot drift."""

from typing import Any, Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, distinct, func
from sqlalchemy.orm import Session, joinedload

from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.services.base import BaseService
from core.services.crud import list_records
from core.utils.encryption import encrypt


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
        "is_active": bool(m.is_active),
        "created_at": int(m.created_at.timestamp()) if m.created_at else None,
        "updated_at": int(m.updated_at.timestamp()) if m.updated_at else None,
    }


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

    # ─── list / aggregate ──────────────────────────────────────────────────

    def list_services(self, body: dict) -> dict:
        """Aggregated list — one row per distinct (provider, service_type)
        the org has ≥1 ApiKey for. A Deepgram STT key and a Deepgram TTS key
        therefore surface as two separate cards on the listing page."""
        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 12), 1), 100)
        search = body.get("search")
        sort_by = body.get("sort_by")
        service_type = body.get("service_type")
        status_filter = body.get("status")

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

        rows = q.offset((page - 1) * page_size).limit(page_size).all()

        provider_ids = [r.provider_id for r in rows if r.provider_id]
        model_count_map = self._model_count_by_provider_kind_map(provider_ids)
        default_map = self._default_keys_by_provider_kind_map(provider_ids)

        def _row_to_dict(r) -> dict:
            pid = str(r.provider_id)
            kind = r.service_type
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
            }

        return {
            "items": [_row_to_dict(r) for r in rows],
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

    def list_providers_catalog(self) -> list[dict]:
        providers = (
            self.db.query(ModelProvider)
            .filter(ModelProvider.is_active.is_(True))
            .order_by(ModelProvider.display_name.asc())
            .all()
        )
        kinds_map = self._provider_kinds_map([p.id for p in providers])
        return [
            {
                "id": str(p.id),
                "slug": p.slug,
                "display_name": p.display_name,
                "description": p.description,
                "kinds": kinds_map.get(str(p.id), []),
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
            # Detail page is scoped to one (provider, kind). Narrow to just
            # that kind regardless of which other kinds the org has keys for.
            q = q.filter(Model.kind == service_type)
        else:
            # Fallback: restrict to the kinds the org actually has active API
            # keys for, so e.g. a Deepgram-STT-only org doesn't see Deepgram's
            # TTS models.
            org_kinds = {
                row[0]
                for row in self.db.query(distinct(ApiKey.service_type))
                .filter(
                    ApiKey.organization_id == self.org_id,
                    ApiKey.provider_id == prov_uuid,
                    ApiKey.is_active.is_(True),
                )
                .all()
                if row[0]
            }
            if org_kinds:
                q = q.filter(Model.kind.in_(org_kinds))

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
            display_name=(body.get("display_name") or "").strip() or None,
            kind=kind,
            description=(body.get("description") or "").strip() or None,
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
            v = (body.get("display_name") or "").strip()
            record.display_name = v or None
        if "kind" in body:
            record.kind = (
                _validate_model_kind(body.get("kind"), required=False) or record.kind
            )
        if "description" in body:
            v = (body.get("description") or "").strip()
            record.description = v or None
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

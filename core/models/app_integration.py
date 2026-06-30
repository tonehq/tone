from typing import Any, Dict

from sqlalchemy import Boolean, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel
from core.utils.encryption import decrypt_json, encrypt_json


class AppIntegration(OrgScopedModel):
    """Catalog of third-party integrations Tone supports (e.g. Google Calendar, HubSpot,
    GitHub). One row per provider type, scoped to an organization so each tenant can
    curate its own list (with seeded defaults shared via the seed script).

    Live tokens for actual user authorizations live in ``oauth_connections``, which references
    this table via ``app_integration_id`` (many connections per integration).

    Provider credentials (``client_id`` / ``client_secret``) live in
    ``encrypted_credentials`` — a Fernet-encrypted JSON blob keyed by credential
    name. Use :meth:`credentials` to read and :meth:`set_credentials` to write.
    """

    __tablename__ = "app_integrations"
    # Slug uniqueness is scoped to the org — two orgs can each have a "hubspot" entry.
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_app_integrations_org_slug"),
    )

    slug = Column(String(64), nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(60), nullable=True, index=True)
    icon_url = Column(String(500), nullable=True)

    # "oauth" | "api_key" | "bearer_token" | "none"
    auth_type = Column(String(20), nullable=False)
    auth_url = Column(String(500), nullable=True)
    token_url = Column(String(500), nullable=True)
    # Post-OAuth ``GET`` endpoint that returns the authorising user's profile
    # (used to capture ``user_email`` on the connection card). Optional —
    # leave null for providers that don't expose one.
    userinfo_url = Column(String(500), nullable=True)
    scopes = Column(JSONB, nullable=True)
    extra_auth_params = Column(JSONB, nullable=True)

    # Encrypted credential blob; shape::
    #   {"client_id": "...", "client_secret": "..."}
    # Stored as ``{"data": "<fernet-string>"}`` via ``encrypt_json`` so the
    # JSONB stays valid while the payload is opaque.
    encrypted_credentials = Column(JSONB, nullable=True)

    pkce_required = Column(Boolean, nullable=False, default=True)

    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=100)

    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    # ──────────────────────────────────────────────────────────────────
    # Credential helpers
    # ──────────────────────────────────────────────────────────────────

    def credentials(self) -> Dict[str, Any]:
        """Decrypt and return the stored credentials dict.

        Returns an empty dict when no credentials are stored — callers can
        therefore always treat the result as a dict without a ``None`` check.
        """
        if not self.encrypted_credentials:
            return {}
        return decrypt_json(self.encrypted_credentials) or {}

    def set_credentials(self, updates: Dict[str, Any]) -> None:
        """Merge ``updates`` into the stored credentials and re-encrypt.

        - Existing keys not present in ``updates`` are preserved.
        - Empty / falsy values in ``updates`` are ignored (use a separate
          ``clear_credentials`` helper if you ever need to remove a key).
        - Setting an empty dict has no effect.
        """
        clean = {k: v for k, v in (updates or {}).items() if v}
        if not clean:
            return
        merged = self.credentials()
        merged.update(clean)
        self.encrypted_credentials = encrypt_json(merged)

    def has_credentials(self) -> bool:
        """Cheap check (no decrypt) for whether *any* credential blob is stored."""
        return bool(self.encrypted_credentials and self.encrypted_credentials.get("data"))

    def is_configured(self) -> bool:
        """True iff this integration has the credentials needed to authorize.

        ``auth_type == "none"`` is always considered configured. Everything
        else needs a ``client_id`` in the encrypted blob; ``client_secret`` is
        optional for public-client PKCE flows.
        """
        if self.auth_type == "none":
            return True
        if not self.has_credentials():
            return False
        return bool(self.credentials().get("client_id"))

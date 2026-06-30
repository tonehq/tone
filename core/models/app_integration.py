import os

from sqlalchemy import Boolean, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class AppIntegration(OrgScopedModel):
    """Catalog of third-party integrations Tone supports (e.g. Google Calendar, HubSpot,
    GitHub). One row per provider type, scoped to an organization so each tenant can
    curate its own list (with seeded defaults shared via the seed script).

    Live tokens for actual user authorizations live in ``oauth_connections``, which references
    this table via ``app_integration_id`` (many connections per integration).

    Secrets are never stored here. ``client_id_env_key`` / ``client_secret_env_key`` are the
    *names* of environment variables that hold the credentials — the values stay in env /
    Infisical so they can be rotated and audited independently of the DB.
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
    scopes = Column(JSONB, nullable=True)
    extra_auth_params = Column(JSONB, nullable=True)

    # Names of env vars holding the credentials (values stay in env / Infisical).
    client_id_env_key = Column(String(120), nullable=True)
    client_secret_env_key = Column(String(120), nullable=True)

    pkce_required = Column(Boolean, nullable=False, default=True)

    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=100)

    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    def is_configured(self) -> bool:
        """True iff the credentials this row points at are present in env.

        ``auth_type == "none"`` is always considered configured. OAuth /
        api_key / bearer_token providers need their referenced ``client_id``
        env var; ``client_secret`` is optional for public-client PKCE flows.

        Pure in-memory check (``os.getenv`` lookups, no DB) so it's safe to
        call inside list loops.
        """
        if self.auth_type == "none":
            return True
        cid_key = self.client_id_env_key
        if not cid_key or not os.getenv(cid_key):
            return False
        secret_key = self.client_secret_env_key
        if secret_key and not os.getenv(secret_key):
            return False
        return True

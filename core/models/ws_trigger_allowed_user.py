from sqlalchemy import Column, String

from core.models.base import TimestampModel


class WsTriggerAllowedUser(TimestampModel):
    """Allowlist of user emails permitted to use the WebSocket ("test bridge") outbound trigger.

    GLOBAL (deployment-wide, not org-scoped): the trigger is an internal test tool, so access is
    granted to specific users regardless of org. Read-only from the app — there is no CRUD API;
    rows are managed directly in the DB. Emails are stored lowercased and looked up
    case-insensitively (see ``OutboundCallService.is_ws_trigger_allowed``).
    """

    __tablename__ = "ws_trigger_allowed_users"

    email = Column(String(255), nullable=False, unique=True, index=True)

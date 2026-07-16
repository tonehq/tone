"""Category G — phone number & channel routing.

Severity is agent_type-aware: inbound calls need a number to route to; outbound
never do; ``both`` warns without a number because the inbound half won't work.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
    Status,
)


class PhoneAssignedIfInboundCheck(ShallowCheck):
    id: ClassVar[str] = "phone.assigned_if_inbound"
    category: ClassVar[Category] = Category.PHONE
    # Severity is agent_type-aware — we escalate to BLOCKER inside run().
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        atype = getattr(ctx.agent, "agent_type", None)
        return atype in {"inbound", "both"}

    def skip_reason(self, ctx: CheckContext) -> str:
        return "Outbound-only agent — no phone number required."

    async def run(self, ctx: CheckContext) -> CheckResult:
        if ctx.phone_numbers:
            return self._pass(
                f"{len(ctx.phone_numbers)} phone number(s) assigned."
            )
        atype = getattr(ctx.agent, "agent_type", None)
        if atype == "inbound":
            # Pure inbound with no phone can't receive any call → hard blocker.
            return CheckResult(
                check_id=self.id,
                category=self.category,
                severity=Severity.BLOCKER,
                status=Status.FAIL,
                message="No phone number is assigned to this agent.",
                remediation=(
                    "Attach a phone number in the Channels tab so inbound "
                    "calls can reach the agent."
                ),
            )
        # "both" — outbound still works.
        return self._fail(
            "No phone number is assigned; only outbound calls will work.",
            remediation="Attach a phone number to also receive inbound calls.",
        )


class PhoneChannelReachableCheck(ShallowCheck):
    """Every assigned phone number must reference a channel with credentials.

    This is a structural check (does the encrypted_config JSONB have contents?)
    — a live provider probe would live in a Deep check, but call channels are
    verified at their own /channel endpoints today.
    """

    id: ClassVar[str] = "phone.channel_reachable"
    category: ClassVar[Category] = Category.PHONE
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return bool(ctx.phone_numbers)

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No phone numbers assigned."

    async def run(self, ctx: CheckContext) -> CheckResult:
        # Local import — Channel model isn't needed by the earlier checks.
        from core.models.channel import Channel

        channel_ids = {p.channel_id for p in ctx.phone_numbers if p.channel_id}
        if not channel_ids:
            return self._fail(
                "One or more phone numbers are not linked to a call channel.",
                remediation="Re-attach the numbers via the Channels tab.",
            )
        channels = (
            ctx.db.query(Channel)
            .filter(
                Channel.id.in_(channel_ids),
                Channel.organization_id == ctx.org_id,
            )
            .all()
        )
        missing_creds = [c for c in channels if not c.encrypted_config]
        if missing_creds:
            names = ", ".join(c.name for c in missing_creds[:3])
            return self._fail(
                f"Channel(s) missing credentials: {names}.",
                remediation="Open the channel and re-enter credentials.",
                resource_ref=ResourceRef(
                    type="channel", id=str(missing_creds[0].id)
                ),
            )
        return self._pass(
            f"All {len(channels)} linked channel(s) have credentials."
        )

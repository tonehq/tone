"""Category G — phone number & channel routing (+ transport credit probe).

Severity is agent_type-aware: inbound calls need a number to route to; outbound
never do; ``both`` warns without a number because the inbound half won't work.

The transport-credit deep check at the bottom of the file lives here (rather
than a sibling ``transport.py``) because it operates on the same ``Channel``
rows the routing checks already reason about — and because "the transport
account has run out of credit" is the single most common runtime failure the
existing structural checks miss.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional, Tuple

from core.services.readiness.base import (
    CheckContext,
    DeepCheck,
    ShallowCheck,
    with_retry,
    with_timeout,
)
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
    Status,
)


# Telephony channel types the transport-credit probe knows how to interrogate.
# Kept module-level so ``applies()`` and the check body reason from one list;
# extending it (e.g. adding "signalwire") means one edit plus a branch in
# ``probes.probe_transport``.
_TELEPHONY_CHANNEL_TYPES = frozenset({"twilio", "telnyx", "plivo", "exotel", "sip"})


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


# ── Deep: live transport credit / account probe ──────────────────────────────


class TransportCreditsReachableCheck(DeepCheck):
    """Verify each configured telephony channel's account is usable.

    For every telephony ``Channel`` linked to the agent (via ``AgentChannel``),
    decrypt its credentials and hit the provider's account/balance endpoint.
    Catches the two failure modes the shallow ``PhoneChannelReachableCheck``
    can't see:

    * credentials that decrypted fine but the provider now rejects (revoked
      auth token, closed account) — surfaces as 401/403.
    * account still authenticated but out of credit / talk-time balance —
      surfaces as either an explicit low balance in the response or a
      quota / payment-required error.

    Does **not** require a phone number to be assigned. An outbound-only
    agent typically has a channel but no number and still needs a funded
    account to place calls.
    """

    id: ClassVar[str] = "phone.transport_credits_reachable"
    category: ClassVar[Category] = Category.TRANSPORT
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        return any(
            (c.channel_type or "").lower() in _TELEPHONY_CHANNEL_TYPES
            and c.encrypted_config
            for c in ctx.channels
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        return "No telephony channel with credentials linked to this agent."

    @with_retry()
    # 6s per provider × up to N channels + JSON parse + retry buffer. Most
    # accounts respond in <500ms; the 15s ceiling keeps a single stuck
    # provider from stalling the report.
    @with_timeout(15.0)
    async def run(self, ctx: CheckContext) -> CheckResult:
        import httpx

        from core.services.readiness.probes import (
            _TRANSPORT_PROBE_TIMEOUT,
            probe_transport,
        )
        from core.utils.encryption import decrypt_json

        # Isolate telephony channels once so the loop and the "no channels"
        # branch reason from the same subset ``applies()`` gated on.
        telephony_channels = [
            c for c in ctx.channels
            if (c.channel_type or "").lower() in _TELEPHONY_CHANNEL_TYPES
        ]

        failed: List[Tuple[str, str]] = []  # (channel_name, reason)
        first_failed_id: Optional[str] = None
        checked = 0

        # One client, reused across all channel probes for connection pooling —
        # same pattern as ``ToolReachableCheck`` and ``McpServerHttpReachableCheck``.
        async with httpx.AsyncClient(timeout=_TRANSPORT_PROBE_TIMEOUT) as client:
            for channel in telephony_channels:
                slug = (channel.channel_type or "").lower()
                try:
                    config = decrypt_json(channel.encrypted_config) or {}
                except Exception:  # noqa: BLE001 — decrypt failure (rotated secret)
                    failed.append((channel.name, "credentials could not be decrypted"))
                    if first_failed_id is None:
                        first_failed_id = str(channel.id)
                    continue

                result = await probe_transport(client, config, slug)
                checked += 1
                if not result.ok:
                    failed.append((channel.name, result.message))
                    if first_failed_id is None:
                        first_failed_id = str(channel.id)

        if not checked and not failed:
            # ``applies()`` guards this, but keep a defensive branch so the
            # method is safe to call directly (tests, ad-hoc reruns).
            return self._skip("No telephony channel with credentials linked to this agent.")

        if failed:
            joined = "; ".join(f"'{n}': {r}" for n, r in failed[:2])
            more = f"; +{len(failed) - 2} more" if len(failed) > 2 else ""
            return self._fail(
                f"Transport probe failed: {joined}{more}",
                remediation=(
                    "Open the failing channel in Integrations → Channels: "
                    "verify the credentials are current and the provider "
                    "account has enough credit / balance to place calls."
                ),
                resource_ref=ResourceRef(type="channel", id=first_failed_id)
                if first_failed_id else None,
            )
        return self._pass(
            f"All {checked} telephony channel(s) authenticated with sufficient balance."
        )

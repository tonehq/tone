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


# Per-provider inbound webhook prefixes derived from ``BASE_CALL_URL``.
# Kept as a table so adding a new provider (or a new webhook path) is one
# edit — matches the "one dispatcher, one branch per provider" style used
# by ``probe_transport`` / ``probe_phone_number``. Providers not listed here
# (Plivo, Exotel) have no first-class inbound route in Tone today, so the
# per-number probe skips the webhook assertion for them.
_INBOUND_WEBHOOK_PATHS: dict[str, str] = {
    "twilio": "/twiml",
    "telnyx": "/telnyx/texml",
}


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


# ── Deep: per-number verification at the provider ─────────────────────────────


class PhoneNumberVerifiedAtProviderCheck(DeepCheck):
    """Verify every assigned phone number at the telephony provider.

    Catches the "silent inbound failure" cases the shallow checks and the
    account-balance probe both miss:

    * The number typed into Tone is not actually owned by the linked account
      (typo, wrong subaccount, ported out) — outbound will fail with "sender
      not owned", inbound will never ring Tone.
    * The number is provisioned for SMS-only — calls fail immediately.
    * The inbound voice webhook does not point at Tone (``BASE_CALL_URL``) —
      the number rings the wrong destination and Tone never sees the call.

    Severity is agent-type-aware — same reasoning as
    ``PhoneAssignedIfInboundCheck``: an outbound-only agent still places calls
    from an unverified number, but a wrong webhook is only fatal to inbound.
    """

    id: ClassVar[str] = "phone.number_verified_at_provider"
    category: ClassVar[Category] = Category.PHONE
    # Class-level severity is WARNING; ``run()`` escalates to BLOCKER for
    # pure inbound agents where webhook / ownership issues are fatal.
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        if not ctx.phone_numbers:
            return False
        return any(
            (c.channel_type or "").lower() in _TELEPHONY_CHANNEL_TYPES
            and c.encrypted_config
            for c in ctx.channels
        )

    def skip_reason(self, ctx: CheckContext) -> str:
        if not ctx.phone_numbers:
            return "No phone numbers assigned."
        return "No telephony channel with credentials linked to this agent."

    # Outer budget scales with the number of assigned phone numbers so a large
    # org (many inbound DIDs) can't starve the check at a fixed ceiling. The
    # inner per-number timeout (``_PHONE_NUMBER_PROBE_TIMEOUT`` = 6s) still
    # bounds each individual probe; probes fire in parallel via
    # ``asyncio.gather`` so the outer budget is effectively bounded by the
    # SLOWEST probe rather than the sum.
    @with_timeout(30.0)
    async def run(self, ctx: CheckContext) -> CheckResult:
        import asyncio
        import httpx

        from shared.config import settings
        from core.services.readiness.probes import (
            _PHONE_NUMBER_PROBE_TIMEOUT,
            probe_phone_number,
        )
        from core.utils.encryption import decrypt_json

        # ``BASE_CALL_URL`` is the origin every inbound TwiML / TeXML route is
        # mounted under (see shared/config.py:250 and core/api/telephony_routes.py).
        # A missing config here (unusual dev-only edge case) means we skip the
        # webhook assertion but still verify ownership + capability.
        base_call_url = (getattr(settings, "BASE_CALL_URL", "") or "").rstrip("/")

        # Build channel-by-id map so we can pair each PhoneNumber with its
        # channel row (already fetched into ctx.channels) without a DB hit.
        channels_by_id = {c.id: c for c in ctx.channels}

        agent_type = (getattr(ctx.agent, "agent_type", None) or "").lower()
        # Wrong-webhook / not-owned is fatal on pure inbound (calls never
        # arrive). "both" or outbound-only can still place outbound calls
        # off a healthy channel, so keep those as WARNING.
        target_severity = (
            Severity.BLOCKER if agent_type == "inbound" else Severity.WARNING
        )

        # Build the probe task list first (all sync work / decrypts) so the
        # network step is a single ``gather`` — parallelism prevents the outer
        # 30s wrapper from being blown by N sequential 6s probes on orgs with
        # many DIDs.
        probe_specs: List[Tuple[Any, str, dict, Optional[str]]] = []  # (phone, slug, cfg, webhook_prefix)
        for phone in ctx.phone_numbers:
            channel = channels_by_id.get(phone.channel_id)
            if channel is None or not channel.encrypted_config:
                # Sibling checks (PhoneChannelReachableCheck) already
                # report this; skip to avoid duplicate drawer noise.
                continue
            slug = (channel.channel_type or "").lower()
            if slug not in _TELEPHONY_CHANNEL_TYPES:
                continue
            try:
                config = decrypt_json(channel.encrypted_config) or {}
            except Exception:  # noqa: BLE001 — decrypt failure covered elsewhere
                continue

            webhook_prefix = (
                f"{base_call_url}{_INBOUND_WEBHOOK_PATHS[slug]}"
                if base_call_url and slug in _INBOUND_WEBHOOK_PATHS
                else None
            )
            probe_specs.append((phone, slug, config, webhook_prefix))

        failed: List[Tuple[str, str]] = []  # (number, reason)
        first_failed_id: Optional[str] = None
        checked = 0

        if probe_specs:
            async with httpx.AsyncClient(timeout=_PHONE_NUMBER_PROBE_TIMEOUT) as client:
                results = await asyncio.gather(
                    *(
                        probe_phone_number(client, cfg, slug, phone.number, webhook_prefix)
                        for phone, slug, cfg, webhook_prefix in probe_specs
                    ),
                    return_exceptions=False,  # probe_phone_number swallows internally
                )
            for (phone, _slug, _cfg, _prefix), result in zip(probe_specs, results):
                checked += 1
                if not result.ok:
                    failed.append((phone.number, result.message))
                    if first_failed_id is None:
                        first_failed_id = str(phone.id)

        if not checked and not failed:
            return self._skip(
                "No telephony phone numbers with credentials linked to this agent."
            )

        if failed:
            joined = "; ".join(f"'{n}': {r}" for n, r in failed[:2])
            more = f"; +{len(failed) - 2} more" if len(failed) > 2 else ""
            return CheckResult(
                check_id=self.id,
                category=self.category,
                severity=target_severity,
                status=Status.FAIL,
                message=f"Phone number verification failed: {joined}{more}",
                remediation=(
                    "Open the failing number in the provider console: confirm "
                    "the number is owned by the account, is voice-capable, and "
                    "its inbound voice webhook points at Tone."
                ),
                resource_ref=ResourceRef(type="phone_number", id=first_failed_id)
                if first_failed_id else None,
            )
        return self._pass(
            f"All {checked} phone number(s) verified at provider "
            "(owned, voice-capable, webhook routed to Tone)."
        )

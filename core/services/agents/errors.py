"""Typed application exceptions for agent-scoped services.

Services raise these; the router layer converts them into HTTP responses (see
``core/api/v1/agent_profile_variables.py::_handle_profile_var_error``). Never
raise ``HTTPException`` inside a service — that would couple business logic to
the API transport and break reuse from workers / CLI / other adapters.
"""

from __future__ import annotations


class ProfileVariableError(Exception):
    """Base class for agent profile-variable service errors."""


class ProfileVariableNotFoundError(ProfileVariableError):
    """Requested profile variable does not exist for this agent/org."""


class ProfileVariableKeyConflictError(ProfileVariableError):
    """Another profile variable with the same key already exists on this agent."""


class ProfileVariableInvalidError(ProfileVariableError):
    """Payload failed validation: bad key format, reserved key, or oversize value."""

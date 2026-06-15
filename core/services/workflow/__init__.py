"""Org-level visual workflow ("pathway") feature.

* ``schema`` — Pydantic models for the canonical React-Flow-native graph + a pure
  ``validate_graph`` function.
* ``vapi_adapter`` — convert between the canonical graph and Vapi's flat export shape.
* ``service`` — :class:`WorkflowService` (CRUD / draft / publish / validate).
"""

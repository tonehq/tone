"""Concrete readiness checks — one class per rule, grouped by category file.

Every module here exports classes that are instantiated once in ``registry.py``.
Nothing here should be imported by anything other than ``registry.py``; treat
these as leaves of the dependency tree.
"""

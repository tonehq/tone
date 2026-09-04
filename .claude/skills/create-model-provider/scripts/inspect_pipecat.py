#!/usr/bin/env python3
"""Introspect a Pipecat service class before wiring it.

Prints the constructor signature and the InputParams field names. Those names are the
contract: build_input_params() silently drops any metadata key that is not an
InputParams field, so meta_data_schema entries MUST match this list.

    python inspect_pipecat.py pipecat.services.xai.tts.XAITTSService
    python inspect_pipecat.py --search sarvam
"""
import dataclasses
import importlib
import inspect
import os
import pkgutil
import sys


def field_names(cls):
    """Field names off a pydantic model or a dataclass — pipecat uses both."""
    if cls is None:
        return []
    if hasattr(cls, "model_fields"):
        return list(cls.model_fields)
    if dataclasses.is_dataclass(cls):
        return [f.name for f in dataclasses.fields(cls)]
    return []


def settings_class(cls, module):
    """The Settings class a settings-based service really reads, if there is one."""
    inner = getattr(cls, "Settings", None)
    if field_names(inner):
        return inner
    candidate = getattr(module, f"{cls.__name__.replace('Service', '')}Settings", None)
    return candidate if field_names(candidate) else None


def _search(term):
    import pipecat.services as services
    hits = [m.name for m in pkgutil.walk_packages(services.__path__, "pipecat.services.")
            if term.lower() in m.name.lower()]
    if not hits:
        print(f"No pipecat.services module matching '{term}'.")
        print("A provider with no Pipecat service class cannot be wired here — the")
        print("service class must be added to the tone-pipecat fork first.")
        return 1
    print(f"Modules matching '{term}':")
    for h in sorted(hits):
        print(f"  {h}")
        try:
            m = importlib.import_module(h)
            for c in sorted(n for n, o in vars(m).items()
                            if inspect.isclass(o) and n.endswith("Service")
                            and o.__module__ == h):
                print(f"      {h}.{c}")
        except Exception as exc:
            print(f"      (import failed: {type(exc).__name__}: {exc})")
    return 0


def main(argv):
    if not argv or argv[0] in ("--help", "-h"):
        print(__doc__)
        return 0 if argv else 1
    if argv[0] in ("--search", "-s"):
        return _search(argv[1]) if len(argv) > 1 else 1

    path = argv[0]
    mod_path, _, cls_name = path.rpartition(".")
    try:
        cls = getattr(importlib.import_module(mod_path), cls_name)
    except Exception as exc:
        print(f"Could not import {path}: {type(exc).__name__}: {exc}")
        print(f"\nTry:  python {os.path.basename(__file__)} --search <vendor>")
        return 1

    print(f"=== {path} ===\n")
    params = {}
    try:
        sig = inspect.signature(cls.__init__)
        params = dict(sig.parameters)
        print("Constructor:")
        for name, p in params.items():
            if name in ("self", "kwargs", "args"):
                continue
            default = "" if p.default is inspect.Parameter.empty else f" = {p.default!r}"
            print(f"  {name}{default}")
    except (TypeError, ValueError):
        print("  (signature unavailable)")

    side = sorted(p for p in params
                  if "function" in p or "map" in p or p in ("server", "url"))
    if side and "model" not in params:
        print(f"\n  !! No `model` argument. Model selection goes through: {', '.join(side)}")
        print("     Passing model= alone will silently use the class default.")
    elif side:
        print(f"\n  NOTE: also takes {', '.join(side)} — confirm whether model selection")
        print("        flows through `model` or one of these.")

    module = importlib.import_module(mod_path)
    settings_cls = settings_class(cls, module) if "settings" in params else None
    ip = getattr(cls, "InputParams", None)
    ip_fields = field_names(ip)

    if settings_cls:
        # A settings-based service ignores params= entirely, and often model= too, so the
        # repo's usual model=/params= call would silently drop everything the user set.
        print(f"\n  !! Constructor takes `settings=`. This service reads "
              f"{settings_cls.__name__}, NOT InputParams.")
        print("     Passing params= has no effect. Build the Settings object in the branch.")
        if "model" not in params:
            print("     There is also no `model` argument — the model goes inside Settings.")
        elif ip_fields:
            print("     `model` may be ignored too when settings is set — verify before relying on it.")
        fields = field_names(settings_cls)
        print(f"\n{settings_cls.__name__} fields — meta_data_schema names MUST match these:")
        for name in fields:
            extra = "  <- not in InputParams" if ip_fields and name not in ip_fields else ""
            print(f"  {name}{extra}")
        print(f"\n  {len(fields)} fields.")
        if ip_fields:
            print(f"  InputParams (inherited, NOT what this service reads) has only "
                  f"{len(ip_fields)}: {', '.join(ip_fields)}")
        return 0

    print("\nInputParams fields — meta_data_schema names MUST match these exactly:")
    if not ip_fields:
        print("  (none — this service takes no params=; omit meta_data_schema fields)")
        return 0
    for name in ip_fields:
        print(f"  {name}")
    print(f"\n  {len(ip_fields)} fields. Anything not in this list is dropped silently.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

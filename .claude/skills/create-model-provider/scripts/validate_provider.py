#!/usr/bin/env python3
"""Validate a dev-data.json provider entry before seeding.

Rules are DERIVED, not hardcoded: required keys and enum values come from analyze.py,
which infers them from the entries already in the file. The one external check is
against the Pipecat class you name, whose InputParams fields are the real contract.

    python validate_provider.py <name>
    python validate_provider.py <name> --service pipecat.services.x.tts.XTTSService
    python validate_provider.py --all
"""
import argparse
import dataclasses
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import SEED, derive_schema, seed_buckets  # noqa: E402

# Keys the factory consumes directly rather than through InputParams, so they are
# legitimate metadata names even when absent from a service's InputParams.
FACTORY_KEYS = {"model", "base_url", "voice_id", "sample_rate", "language"}


def validate(prov, layer, schema, service_path=None):
    errors, warnings = [], []
    rules = schema[layer]
    enums = rules["enums"]

    for key in rules["provider_keys_required"]:
        if key not in prov:
            errors.append(f"missing key {key!r} — present on every other {layer} provider")
    if enums.get("provider_type") and prov.get("provider_type") not in enums["provider_type"]:
        errors.append(f"provider_type={prov.get('provider_type')!r}; "
                      f"existing entries use {enums['provider_type']}")
    if prov.get("provider_type") != layer:
        errors.append(f"provider_type={prov.get('provider_type')!r} but sits in "
                      f"{rules['bucket']}")
    if enums.get("status") and str(prov.get("status")) not in enums["status"]:
        errors.append(f"status={prov.get('status')!r}; existing use {enums['status']}")
    if not prov.get("api_key_env"):
        errors.append("no api_key_env — the resolver returns no spec when the key is "
                      "falsy, so the agent runs with this service missing entirely")
    if (prov.get("description") or "").strip().upper().endswith(("LLM", "STT", "TTS")):
        warnings.append("description ends with a layer suffix — seed strips it, and a "
                        "multi-layer vendor keeps only the first bucket's text")

    declared = {f.get("name") for f in (prov.get("meta_data_schema") or []) if f.get("name")}

    def check_fields(spec, where):
        for field in spec or []:
            fname = field.get("name")
            if not fname:
                errors.append(f"{where}: metadata field with no name")
                continue
            for attr in ("data_type", "type"):
                allowed = enums.get(attr)
                if allowed and field.get(attr) not in allowed:
                    errors.append(f"{where}.{fname}: {attr}={field.get(attr)!r}; "
                                  f"existing entries use {allowed}")
            if not field.get("description"):
                warnings.append(f"{where}.{fname}: no description — unlabelled control")

    check_fields(prov.get("meta_data_schema"), "provider")

    if not prov.get("models"):
        errors.append("no models — provider will be unselectable")
    seen = set()
    for model in prov.get("models") or []:
        mname = model.get("name")
        if not mname:
            errors.append("model with no name")
            continue
        if mname in seen:
            errors.append(f"duplicate model name {mname!r}")
        seen.add(mname)
        for key in rules["model_keys_required"]:
            if key not in model:
                warnings.append(f"model {mname}: no {key!r} — every other model has it")
        meta = model.get("meta_data") or {}
        if "model" not in meta:
            errors.append(f"model {mname}: meta_data.model missing — metadata is passed "
                          f"through, so the vendor receives no model id")
        check_fields(model.get("meta_data_schema"), f"model {mname}")
        declared |= {f.get("name") for f in (model.get("meta_data_schema") or [])
                     if f.get("name")}

    if "voices" in (rules["provider_keys_required"] + rules["provider_keys_optional"]):
        for voice in prov.get("voices") or []:
            vid = voice.get("voice_id") or voice.get("name") or "<unnamed>"
            if not voice.get("voice_id"):
                errors.append(f"voice {vid}: no voice_id")
            if not voice.get("language_list"):
                warnings.append(f"voice {vid}: no language_list — ModelLanguage rows "
                                f"derive from it, so the language picker stays empty")

    if service_path:
        try:
            mod, _, cls_name = service_path.rpartition(".")
            cls = getattr(importlib.import_module(mod), cls_name)
            ip = getattr(cls, "InputParams", None)
            settings_cls = getattr(cls, "Settings", None)
            valid = set(ip.model_fields) if ip is not None else set()
            contract = "InputParams"
            if settings_cls is not None and dataclasses.is_dataclass(settings_cls):
                # A class exposing Settings is configured through settings=, which wins
                # over the deprecated params=/model= kwargs wherever both are accepted.
                valid |= {f.name for f in dataclasses.fields(settings_cls)}
                contract = "InputParams/Settings" if ip is not None else "Settings"
            if not valid:
                if declared - FACTORY_KEYS:
                    errors.append(
                        f"{cls_name} has no InputParams and no Settings, so the factory "
                        f"drops every metadata field: "
                        f"{', '.join(sorted(declared - FACTORY_KEYS))}.")
            else:
                for field in sorted(declared - FACTORY_KEYS):
                    if field not in valid:
                        errors.append(
                            f"metadata field {field!r} is not a {contract} field of "
                            f"{cls_name} — dropped silently. Valid: "
                            f"{', '.join(sorted(valid)) or '(none)'}")
        except Exception as exc:
            warnings.append(f"could not introspect {service_path}: "
                            f"{type(exc).__name__}: {exc}")

    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", nargs="?")
    ap.add_argument("--service")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if not args.provider and not args.all:
        ap.error("give a provider name or --all")

    seed = json.load(open(SEED))
    buckets = seed_buckets(seed)
    schema = derive_schema(seed, buckets)

    # --service names one class, which belongs to one layer. Applying it to a vendor's
    # other layers would flag every field on an entry the class has nothing to do with.
    service_layer = None
    if args.service:
        low = args.service.lower()
        for layer in schema:
            if f".{layer}." in low or low.endswith(layer):
                service_layer = layer
                break

    total = 0
    for bucket, layer in buckets.items():
        for prov in seed[bucket]:
            if not args.all and prov.get("name") != args.provider:
                continue
            svc = args.service if (not service_layer or service_layer == layer) else None
            errors, warnings = validate(prov, layer, schema, svc)
            if errors or warnings:
                print(f"\n{bucket}/{prov.get('name')}")
                for e in errors:
                    print(f"  ERROR   {e}")
                for w in warnings:
                    print(f"  warning {w}")
            elif not args.all:
                print(f"{bucket}/{prov.get('name')}: OK")
            total += len(errors)

    print(f"\n{total} error(s)." if total else "\nNo errors.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

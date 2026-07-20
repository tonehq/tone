"""
Seed a NEW ORGANIZATION on an existing Tone database.

Assumes the DB is already migrated and the global provider catalogue
(ModelProvider / Model / ModelVoice / ModelLanguage) is already seeded
via ``dev/seed.py`` (or ``bootstrap/db-bootstrap.sh``). This script only creates
the org-scoped rows:

  1. User (owner)
  2. Organization
  3. Member (owner)
  4. ApiKey rows            — optional, gated by --api-keys-from-env
  5. app_integrations rows  — chained via dev.seed_app_integrations
  6. built-in Tool rows     — chained via dev.seed_built_in_tools

Reuses the small helpers already defined in ``dev/seed.py``
(``seed_user``, ``seed_organization``, ``seed_member``, ``load_seed_data``,
``_get_api_key_from_env``, ``_run_chained_seeder``) so the two flows stay
in sync.

Usage:
    python dev/seed_org.py                       # prompts; skips API keys
    python dev/seed_org.py --api-keys-from-env   # also seed API keys from env
"""
import argparse
import os
import sys
import time
from datetime import datetime

# Ensure project root is on path when run as script
if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()

from dev.seed import (  # noqa: E402  (import after sys.path fix)
    _get_api_key_from_env,
    _run_chained_seeder,
    _slugify,
    load_seed_data,
    prompt_setup_inputs,
    seed_contact_directory,
    seed_member,
    seed_organization,
    seed_user,
)


class OrgSeedError(Exception):
    """Raised for expected, user-facing failures (missing catalogue,
    duplicate email/org). Caught in ``main()`` and printed cleanly —
    unlike raw DB IntegrityError tracebacks, which are hostile."""


class OrgSeeder:
    """Seeds a single new organization onto an already-populated DB.

    Encapsulates the org-level flow so it can also be called
    programmatically (e.g. from an admin API in future) — not just from
    the CLI. Global catalogue seeding (providers/models/voices) is out
    of scope; use ``dev/seed.py`` for that.

    Attributes:
        db: An open SQLAlchemy session (caller owns lifecycle).
        org_name / email / password: Prompted inputs.
        seed_api_keys: If True, encrypt env-var values and insert one
            ApiKey per (provider, service_type). If False, skip entirely.
        stats: Populated during ``run()`` for the CLI summary.
    """

    def __init__(
        self,
        db,
        org_name: str,
        email: str,
        password: str,
        seed_api_keys: bool = False,
    ):
        self.db = db
        self.org_name = org_name
        self.email = email
        self.password = password
        self.seed_api_keys = seed_api_keys
        self.stats = {
            "user_created": False,
            "org_created": False,
            "member_created": False,
            "api_keys_created": 0,
            "api_keys_none": 0,
            "api_keys_skipped": 0,
            "contact_directory_created": False,
        }

    def run(self):
        """Execute the seed and commit. Returns (stats, organization).

        Raises ``OrgSeedError`` on pre-flight failures (empty catalogue,
        duplicate email, duplicate org slug) so the CLI can print a clean
        message instead of a stack trace.
        """
        self._preflight_catalogue()
        self._preflight_duplicates()

        user = seed_user(self.db, self.email, self.password)
        self.stats["user_created"] = True

        org = seed_organization(self.db, self.org_name)
        self.stats["org_created"] = True

        seed_member(self.db, user, org)
        self.stats["member_created"] = True

        # Mirror dev/seed.py: pin the owner's default org.
        user.organization_id = org.id

        if self.seed_api_keys:
            self._seed_api_keys_from_env(org.id)

        # Default 'Global' ContactDirectory + its CSV datasource.
        # ContactDirectoryService commits internally, which persists the
        # pending user/org/member and any API-key rows above — so the
        # trailing db.commit() becomes a safe no-op.
        seed_contact_directory(self.db, org.id, user.id)
        self.stats["contact_directory_created"] = True

        self.db.commit()
        return self.stats, org

    # ── internals ────────────────────────────────────────────────────
    def _preflight_catalogue(self):
        """Bail out if the global provider catalogue hasn't been seeded.
        Without it, the new org would have no LLM/STT/TTS to work with."""
        from core.models.model_provider import ModelProvider

        if self.db.query(ModelProvider).count() == 0:
            raise OrgSeedError(
                "No ModelProvider rows found in the database.\n"
                "   The global provider catalogue must be seeded first.\n"
                "   Run:  ./bootstrap/db-bootstrap.sh   (or:  python dev/seed.py)"
            )

    def _preflight_duplicates(self):
        """Check email + org slug uniqueness up front so the caller gets
        a friendly message instead of a raw IntegrityError on commit."""
        from core.models.organization import Organization
        from core.models.user import User

        if self.db.query(User).filter_by(email=self.email).first():
            raise OrgSeedError(
                f"Email '{self.email}' already exists.\n"
                "   Choose a different owner email or delete the existing user."
            )

        slug = _slugify(self.org_name)
        if self.db.query(Organization).filter_by(slug=slug).first():
            raise OrgSeedError(
                f"Organization slug '{slug}' already exists "
                f"(derived from name '{self.org_name}').\n"
                "   Choose a different org name."
            )

    def _seed_api_keys_from_env(self, org_id):
        """Insert one ApiKey per (provider, service_type) for this org.

        Providers must already exist in the DB — matched by ``provider_id``
        string against ``dev-data.json``. Missing providers are silently
        skipped (operator should re-run ``dev/seed.py`` first if
        ``dev-data.json`` has grown since the DB was seeded). Missing env
        vars are counted in ``stats["api_keys_none"]`` but never fail the run.
        """
        from core.models.api_key import ApiKey
        from core.models.model_provider import ModelProvider
        from core.utils.encryption import encrypt

        all_providers = self._load_all_providers()

        db_providers = {
            mp.provider_id: mp for mp in self.db.query(ModelProvider).all()
        }
        existing_keys = {
            (k.provider_id, k.service_type)
            for k in self.db.query(ApiKey).filter_by(organization_id=org_id).all()
        }

        seen = set()
        for config in all_providers:
            api_key_value = _get_api_key_from_env(config.get("api_key_env"))
            if not api_key_value:
                self.stats["api_keys_none"] += 1
                continue

            mp = db_providers.get(config["name"])
            if not mp:
                continue  # provider absent in DB — global seed hasn't run for it

            kind = config["provider_type"]
            key = (mp.id, kind)
            if key in seen or key in existing_keys:
                self.stats["api_keys_skipped"] += 1
                continue
            seen.add(key)

            self.db.add(
                ApiKey(
                    organization_id=org_id,
                    provider_id=mp.id,
                    service_type=kind,
                    label=f"seed ({kind})",
                    encrypted_key=encrypt(api_key_value),
                    is_active=True,
                )
            )
            self.stats["api_keys_created"] += 1

        self.db.flush()

    @staticmethod
    def _load_all_providers():
        data = load_seed_data()
        return [
            *data.get("llm_providers", []),
            *data.get("stt_providers", []),
            *data.get("tts_providers", []),
        ]


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Seed a new organization on an existing Tone DB.",
    )
    parser.add_argument(
        "--api-keys-from-env",
        action="store_true",
        help=(
            "If set, encrypt provider API keys from environment variables "
            "(OPENAI_API_KEY, DEEPGRAM_API_KEY, etc.) and attach them to the "
            "new org. Otherwise, no ApiKey rows are inserted."
        ),
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    from core.database.session import get_db_script

    org_name, email, password = prompt_setup_inputs()

    db = get_db_script()
    started_at = datetime.now()
    start = time.perf_counter()
    print(f"\nOrg seed started at: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if args.api_keys_from_env:
        print("Mode: API keys WILL be seeded from environment variables.")
    else:
        print("Mode: API keys will NOT be seeded (add them later via the UI).")

    try:
        seeder = OrgSeeder(
            db=db,
            org_name=org_name,
            email=email,
            password=password,
            seed_api_keys=args.api_keys_from_env,
        )
        try:
            stats, org = seeder.run()
        except OrgSeedError as exc:
            db.rollback()
            print(f"\n✗ Cannot seed organization:\n   {exc}")
            sys.exit(1)

        print("\n✓ Org setup complete:")
        print(f"   User:             created ({email})")
        print(f"   Org:              created ({org_name})")
        print(f"   Member:           created (owner)")
        if args.api_keys_from_env:
            print(
                f"   API keys:         {stats['api_keys_created']} created, "
                f"{stats['api_keys_skipped']} already existed, "
                f"{stats['api_keys_none']} no env key"
            )
        else:
            print("   API keys:         skipped (pass --api-keys-from-env to seed)")
        print(
            f"   Contact Directory: {'created' if stats['contact_directory_created'] else 'skipped'} (Global)"
        )

        # Scope the chained seeders to the new org only — avoids re-scanning
        # every existing org on each new-org bootstrap. Both seeders open
        # their own DB sessions, so they don't share our transaction.
        _run_chained_seeder(
            "app_integrations",
            "dev.seed_app_integrations",
            kwargs={"org_id": org.id},
        )
        _run_chained_seeder(
            "built-in tools",
            "dev.seed_built_in_tools",
            kwargs={"org_id": org.id},
        )
    finally:
        db.close()
        ended_at = datetime.now()
        elapsed = time.perf_counter() - start
        print(f"\nOrg seed started: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Org seed ended:   {ended_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total time:       {elapsed:.2f}s")


if __name__ == "__main__":
    main()

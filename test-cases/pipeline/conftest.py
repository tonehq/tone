"""Pipeline test configuration."""

import os

# Force core edition for pipeline tests (no EE dependencies)
os.environ.setdefault("IS_EE", "false")
os.environ.setdefault("SKIP_LICENSE_CHECK", "true")

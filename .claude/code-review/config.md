# code-review config

Controls what `code-review` loads and how it reviews in THIS repo. code-review reads this file in full
every review. Delete the lines you don't need; keep it short.

include:
# Force-load anything code-review should use when reviewing here — not just skills. Each entry is a
# SKILL, a PLUGIN, or an MCP server/tool. Leave blank to auto-detect the standards from the codebase.
#
# Skills:
#   - marketplace skill by NAME (loads from the tonehq-skills marketplace):  backend-standards
#   - marketplace skill by NAME:                                             frontend-standards
#   - repo-local skill by PATH (lives only in this repo, under .claude/skills/):  .claude/skills/architecture/
#
# Plugins — by name (must be enabled); code-review loads the plugin's skills/commands:
#   - some-plugin@tonehq-skills
#
# MCP servers / tools — by name; code-review uses them where relevant:
#   - postman              # the Postman MCP (see the `postman:` key below to name the collection)
#
# Where each comes from in THIS repo (code-review loads/uses them — it never installs or connects them):
#   • repo-local skill → .claude/skills/<name>/            (auto-discovered)
#   • plugin           → enabled in .claude/settings.json  (extraKnownMarketplaces + enabledPlugins)
#   • MCP server       → defined in .mcp.json              (project-scoped) or settings.json mcpServers
# If something listed here isn't available, code-review says so in the report and continues (no silent skip).

exclude:
# Standards to never load here. e.g. frontend-standards, react-vite-frontend-standards
# (a backend-only repo would exclude both frontend standards)

overrides:
# Repo-specific rules that supersede the generic standard (they rank below CLAUDE.md/RULES.md).
# - Migrations use <repo's tool>, not Alembic.
# - Tenancy key is `workspace_id`, resolved by `get_workspace()`.

postman:
# The Postman collection (and optional OpenAPI spec) this repo's API maps to, so the review can diff API
# changes against them READ-ONLY when the diff touches backend API surface. code-review NEVER writes to
# Postman and NEVER runs a collection against a live API.
#   collection: <name-or-id>   # which collection to diff against (omit to auto-detect the repo's collection)
#   spec: app/openapi.json     # optional: a repo OpenAPI spec file to also diff against (omit to skip)
#   disable                    # skip the whole API-contract check entirely
#
# Connecting the Postman MCP (code-review references it — it never installs or connects it):
#   • Easiest: install the official Postman plugin, which bundles a .mcp.json:
#       /plugin install postman@claude-plugins-official      (then /postman:setup to auth)
#   • Or connect the Postman MCP yourself in .mcp.json / settings.json mcpServers.
#   • Auth: OAuth (recommended) or the POSTMAN_API_KEY env var.
#   • Prefer a READ-ONLY tool mode — set POSTMAN_MCP_MODE=code (~24 read-only tools) since this check is
#     report-only; it never needs write tools.
# If the MCP isn't connected, the review says so and lists what would need updating from the diff alone.

research:
# Which MCP servers/tools to prefer when validating a finding.
# - Prefer the GitNexus code-graph MCP for internal questions.

paths:
# Extra sources code-review should read IN FULL, beyond this folder. Each entry is a file, a directory
# (every .md under it is read), or a glob. Relative to the repo root, or an absolute path. Use it to
# pull in shared standards that live elsewhere instead of duplicating them here.
# - docs/architecture/
# - packages/*/STRUCTURE.md
# - ../shared-standards/code-review/

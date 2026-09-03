# plan-mode config

Controls what `plan-mode` loads and how it plans in THIS repo. plan-mode reads this file in full every
plan. Delete the lines you don't need; keep it short.

include:
# Force-load anything plan-mode should use when planning here — not just skills. Each entry is a
# SKILL, a PLUGIN, or an MCP server/tool. Leave blank to auto-detect the standards from the codebase.
#
# Skills:
#   - marketplace skill by NAME (loads from the tonehq-skills marketplace):  backend-standards
#   - marketplace skill by NAME:                                             frontend-standards
#   - repo-local skill by PATH (lives only in this repo, under .claude/skills/):  .claude/skills/architecture/
#     └─ the `architecture` skill is THIS repo's code & file structure (it replaces a structure.md file;
#        create it at .claude/skills/architecture/ with the repo's real layout).
#
# Plugins — by name (must be enabled); plan-mode loads the plugin's skills/commands:
#   - some-plugin@tonehq-skills
#
# MCP servers / tools — by name; plan-mode uses them where relevant (code-graph lookups, data, etc.):
#   - gitnexus            # e.g. the GitNexus code-graph MCP (also see `research:` for research-time prefs)
#
# Where each comes from in THIS repo (plan-mode loads/uses them — it never installs or connects them):
#   • repo-local skill → .claude/skills/<name>/            (auto-discovered)
#   • plugin           → enabled in .claude/settings.json  (extraKnownMarketplaces + enabledPlugins)
#   • MCP server       → defined in .mcp.json              (project-scoped) or settings.json mcpServers
# If something listed here isn't available, plan-mode says so in the plan and continues (no silent skip).

exclude:
# Standards to never load here. e.g. frontend-standards, react-vite-frontend-standards
# (a backend-only repo would exclude both frontend standards)

overrides:
# Repo-specific rules that supersede the generic standard (they rank below CLAUDE.md/RULES.md).
# - Migrations use <repo's tool>, not Alembic.
# - Tenancy key is `workspace_id`, resolved by `get_workspace()`.

research:
# Which MCP servers/tools to prefer when researching this repo.
# - Prefer the GitNexus code-graph MCP for internal questions.

paths:
# Extra sources plan-mode should read IN FULL, beyond this folder. Each entry is a file, a directory
# (every .md under it is read), or a glob. Relative to the repo root, or an absolute path. Use it to
# pull in shared standards that live elsewhere instead of duplicating them here.
# - docs/architecture/
# - packages/*/STRUCTURE.md
# - ../shared-standards/plan-mode/

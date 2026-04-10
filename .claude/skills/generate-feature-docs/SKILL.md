---
name: generate-feature-docs
description: >
  Generate comprehensive feature/page documentation for this codebase that enables
  Claude Code to work on bugs and new features WITHOUT reading source files — reducing
  token usage by ~90%. Use this skill when the user asks to document a page, feature,
  component, or module, or says things like 'create docs for', 'document this feature',
  'generate docs', 'reduce token usage', or 'I want docs like the QC checksheet docs'.
  Also use when the user mentions wanting to save tokens, reduce context, or create a
  reference doc for future conversations.
---

# Feature Documentation Generator

Generate comprehensive feature documentation that serves as a **source code replacement**
for future Claude Code sessions. A developer (or Claude) can debug issues and implement
new features by reading the doc instead of the source files — cutting token usage by ~90%.

## Process

### Phase 1: Identify scope

If no target is specified, ask the user. Then identify ALL related files using the Explore agent:

1. Page components (`src/app/`)
2. Child components (`src/components/`)
3. Custom hooks (`src/hooks/`)
4. Services (`src/services/`)
5. Atoms/state (`src/atoms/`)
6. Types (`src/types/`)
7. Utilities (`src/utils/`)
8. Constants (`src/constants/`)

### Phase 2: Deep read with parallel agents

Launch 3-5 Explore agents in parallel to read ALL related files. Each agent focuses on
one area (pages+components, services+atoms+types, utils+constants).

For each file, capture:
- All state variables (local, atoms, URL params)
- All useEffect hooks (deps, triggers, what they do)
- All functions (params, logic, return value)
- All props interfaces
- JSX structure and conditional rendering
- API calls (endpoints, payloads, responses)

### Phase 3: Write the documentation

Create the doc at `docs/{FEATURE_NAME}_DOCUMENTATION.md` following the template in
`references/doc-template.md`. Read that file before writing.

### Phase 4: Verify completeness

After writing, verify against this checklist:

- [ ] Every state variable documented (local, atoms, refs, derived)
- [ ] Every useEffect with deps AND logic (not just "fetches data")
- [ ] Every function with params AND behavior (not just "handles click")
- [ ] Every props interface with ALL fields
- [ ] Complex algorithms documented step-by-step
- [ ] API payload with field renames and type transforms
- [ ] Conditional rendering logic (what shows when)
- [ ] Status/enum values with labels and special behaviors
- [ ] "How to Extend" section with common scenarios
- [ ] File index with sizes

Fix any gaps found.

## What NOT to document

- Import paths (change frequently — document what's imported, not exact paths)
- CSS class names or exact pixel values (unless they affect behavior)
- Third-party library internals (MUI, D3, etc.)
- Git history or who wrote what
- Test files (document testable behaviors instead)

## Output

Save to `docs/{FEATURE_NAME}_DOCUMENTATION.md`. Report token savings:
- Count total source file sizes
- Doc is typically ~5-10% of source size
- Token reduction ~ 90-95% for most tasks

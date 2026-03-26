# Documentation Template

Use this structure for every feature doc. Adapt sections as needed — skip sections
that don't apply (e.g., Queue Systems for a simple page), but never skip Navigation,
Page Component, Atoms, Service Layer, or File Index.

---

## Template

```markdown
# {Feature Name} — Complete Documentation

> This document covers the entire {feature} page: components, hooks, services,
> atoms, types, and navigation. It is designed so that Claude Code can understand
> the feature without reading source files directly.

---

## Table of Contents
(numbered list of all sections)

---

## 1. Navigation & Routing
- Route path with URL params table
- Navigation flow diagram (ASCII art showing how users get here and leave)
- Route constants

## 2. Page Component
- File path and size
- All state (local, atoms, derived) as a table: Variable | Type | Purpose
- All useEffect hooks: number them, document deps AND logic
- All handler functions: name, params, step-by-step logic
- **useMemo computations** — document the logic, not just "it computes X"
- JSX structure (tree diagram)
- Props passed to each child component

## 3. Core Hook (if exists)
- Parameters
- All internal state (useState, atoms, refs — every single one)
- All derived values
- All useEffect hooks (numbered, deps and logic)
- All functions with detailed logic:
  - Complex functions (>50 lines): step-by-step algorithm
  - Matching/filtering: exact match criteria
  - State mutations: what fields change and how
  - Debounced functions: timing and triggers
- Return value (complete list)

## 4. Child Components
For each component:
- File path and size
- Full props interface (every prop with type)
- Key functionality
- Internal logic that affects behavior
- Child components it renders

Include a component dependency tree (ASCII art).

## 5. Atoms (Global State)
For each atom:
- State structure (TypeScript interface)
- Default value
- All action atoms with purpose
For complex action atoms:
- Document the FULL algorithm step-by-step
- Document merge priority and conflict resolution

## 6. Type Definitions
- Every interface with every field and type
- Field descriptions for non-obvious fields
- Group by file

## 7. Service Layer
- Function table: name | endpoint | method | purpose
- For each function: request payload, response shape, error handling
- **API payload format** — document field renames and type transforms

## 8. Queue Systems (if applicable)
- Queue key format
- Queue item structure
- Processing flow
- API endpoint and payload

## 9. Database Operations (if applicable)
- Function table: name | SQL operation | returns
- Table schema: all columns with types

## 10. Utility Functions
- Function table: name | purpose
- For complex utilities: document exact logic

## 11. API Endpoints
- Table: constant name | path | method | purpose

## 12. Key Concepts & Patterns
- Domain-specific concepts
- Status codes with labels and behaviors
- Bidirectional data flows between pages
- Authentication/authorization patterns

## 13. How to Extend (Common Scenarios)
For each likely extension scenario:
- Files to modify (ordered list)
- Step-by-step instructions
- Interface/type definitions needed
- Gotchas and conventions

## 14. File Index
- Table: file path | size | purpose
- Grouped by category (pages, hooks, components, services, etc.)
- Total source size
```

---

## Quality Standards

- Every string/label must come from source code, not guessing
- Use tables for structured data (state, props, endpoints)
- Use ASCII tree diagrams for component hierarchy
- Use code blocks for TypeScript interfaces and type definitions
- Document conditional rendering: what shows when and why
- Include token savings estimate at the bottom

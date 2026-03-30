# RULES.md — Feature Documentation Index & Workflow Rules

> Read this file at the start of every conversation. It maps features to documentation files so you can understand context without reading source files directly.

---

## Rule 1: Always Read Docs Before Source Code

Before reading ANY source file for debugging or implementation, check if a feature doc exists below. Read the relevant doc FIRST — it contains all state, effects, handlers, props, types, services, and extension guides. Only read the specific source file you need to EDIT.

**This reduces token usage by ~90%.** Reading docs replaces reading dozens of source files.

---

## Rule 2: Feature → Documentation Mapping

### Docs Folder Structure

```
docs/
├── RULES.md                         # THIS FILE — index & workflow rules
├── AUTH_FLOW_DOCUMENTATION.md       # Auth feature (login, signup, password reset, etc.)
├── design.md                        # Design system reference (theme tokens, spacing, patterns)
├── shared-components.md             # Shared component API reference
└── features/
    └── settings-page.md             # Settings page (API Keys, Members, Organization)
```

### Quick Lookup Table

| If working on... | Read this doc first |
|-------------------|-------------------|
| Login, signup, forgot password, reset password, email verification, auth cookies/tokens | `docs/AUTH_FLOW_DOCUMENTATION.md` |
| Settings page, API keys, integrations, channels (Twilio) | `docs/features/settings-page.md` |
| Team members, invitations, roles, member management | `docs/features/settings-page.md` |
| CustomTable, CustomButton, TextInput, SelectInput, CustomModal, form fields | `docs/shared-components.md` |
| Theme tokens, colors, spacing, design patterns | `docs/design.md` |
| Agents (list, create, edit, form tabs, voice, prompt) | **No doc yet** — generate with `/generate-feature-docs agents` |
| Call history, call logs, transcription, filters | **No doc yet** — generate with `/generate-feature-docs call-history` |
| Phone numbers, Twilio phone number assignment | **No doc yet** — generate with `/generate-feature-docs phone-numbers` |
| Dashboard/home page, stats, quick actions | **No doc yet** — generate with `/generate-feature-docs home` |
| Sidebar, layout, navigation, user menu | **No doc yet** — generate with `/generate-feature-docs layout` |

### Detailed Feature Mapping

#### Authentication (`docs/AUTH_FLOW_DOCUMENTATION.md` — 1,629 lines)
- `src/app/auth/login/LoginPage.tsx` — Login form
- `src/app/auth/signup/SignupClient.tsx` — Signup form with org check
- `src/app/auth/forgotpassword/page.tsx` — Forgot password form
- `src/app/auth/reset-password/page.tsx` — Reset password with token
- `src/app/auth/check-email/page.tsx` — Email sent confirmation
- `src/app/auth/verify_signup/page.tsx` — Email verification handler
- `src/app/auth/shared/ContainerComponent.tsx` — Auth layout with branding
- `src/services/auth/helper.tsx` — Auth API calls + token management
- `src/atoms/AuthAtom.tsx` — Jotai auth state (user, login, logout)
- `src/schemas/auth.ts` — Zod validation schemas
- `src/middleware.ts` — Route protection
- `src/utils/axios.ts` — Axios instance with auth headers
- `src/utils/jwt.tsx` — JWT decoder
- `src/constants/index.ts` — Auth cookie/URL constants

#### Settings & Members (`docs/features/settings-page.md` — 601 lines)
- `src/app/(dashboard)/settings/page.tsx` — Settings page
- `src/components/settings/Integrations.tsx` — Integrations management
- `src/components/settings/Members.tsx` — Members management
- `src/components/settings/Apikeys.tsx` — API keys display
- `src/components/settings/PublicKeysTab.tsx` — Public keys
- `src/components/settings/AddChannelModal.tsx` — Add channel modal
- `src/components/settings/IntegrationsTable.tsx` — Integrations table
- `src/components/settings/InvitationsTable.tsx` — Invitations table
- `src/components/settings/InviteMemberModal.tsx` — Invite member modal
- `src/components/settings/MembersTable.tsx` — Members table
- `src/services/channelService.ts` — Channel CRUD
- `src/services/userService.ts` — User/member operations
- `src/atoms/SettingsAtom.tsx` — Members, invitations, roles state
- `src/atoms/IntegrationAtom.tsx` — Channels/integrations state
- `src/types/integration.ts` — Integration types
- `src/types/settings/members.ts` — Member/invite types

#### Shared UI Components (`docs/shared-components.md` — 908 lines)
- `src/components/shared/*` — 29 shared components
- `src/components/shared/SidebarComponent/*` — Sidebar sub-components
- `src/types/components.ts` — Component prop types

#### Design System (`docs/design.md` — 246 lines)
- Theme tokens, colors (`#8b5cf6` primary purple)
- Spacing conventions
- Component patterns

---

### Undocumented Features (source files only)

#### Agents (~130KB across ~14 files)
- `src/app/(dashboard)/agents/` — Agent routes (list, create inbound/outbound, edit)
- `src/components/agents/AgentListPage.tsx` — Agent list table
- `src/components/agents/AgentFormPage.tsx` — Agent create/edit wrapper
- `src/components/agents/CreateAgentModal.tsx` — Create agent modal
- `src/components/agents/AgentActionMenu.tsx` — Agent context menu
- `src/components/agents/AgentTypeBadge.tsx` — Agent type badge
- `src/components/agents/AssignPhoneNumberModal.tsx` — Phone number assignment
- `src/components/agents/agent-form/GeneralTab.tsx` — General settings tab
- `src/components/agents/agent-form/VoiceTab.tsx` — Voice settings tab
- `src/components/agents/agent-form/VoiceSelect.tsx` — Voice dropdown
- `src/components/agents/agent-form/CallConfigurationTab.tsx` — Call config tab
- `src/components/agents/agent-form/promptPage.tsx` — Prompt/knowledge base tab
- `src/components/agents/agent-form/DynamicProviderFields.tsx` — Dynamic provider fields
- `src/services/agentsService.ts` — Agent CRUD API
- `src/services/voiceService.ts` — TTS voice API
- `src/services/providerService.ts` — Provider API
- `src/atoms/AgentsAtom.tsx` — Agent list state
- `src/atoms/ProviderAtom.tsx` — Provider state
- `src/types/agent.ts` — Agent types
- `src/types/provider.ts` — Provider types
- `src/utils/agentFormUtils.ts` — Form state transformations

#### Call History (~39KB across ~5 files)
- `src/app/(dashboard)/call-history/page.tsx` — Call history page
- `src/components/call-history/CallHistory.tsx` — Call history table
- `src/components/call-history/CallDetailDrawer.tsx` — Call detail drawer
- `src/components/call-history/FilterSortModal.tsx` — Filter modal
- `src/components/call-history/SortModal.tsx` — Sort modal
- `src/components/call-history/TranscriptionModal.tsx` — Transcription modal
- `src/services/callLogService.ts` — Call log API
- `src/atoms/CallLogAtom.tsx` — Call log state
- `src/types/callLog.ts` — Call log types

#### Phone Numbers (in progress)
- `src/app/(dashboard)/phone-numbers/page.tsx` — Phone numbers page
- `src/services/phoneNumberService.ts` — Twilio phone number API

#### Home / Dashboard
- `src/app/(dashboard)/home/page.tsx` — Dashboard with stats and quick actions

#### Layout & Navigation
- `src/app/(dashboard)/layout.tsx` — Dashboard layout
- `src/components/shared/MainLayout.tsx` — Main layout container
- `src/components/shared/SidebarComponent/` — Sidebar (6 sub-components)
- `src/components/shared/userMenu.tsx` — User profile menu
- `src/components/shared/ThemeProvider.tsx` — Theme provider
- `src/components/shared/ThemeToggle.tsx` — Theme toggle
- `src/components/shared/Logo.tsx` — Logo component
- `src/constants/sidebar.ts` — Sidebar navigation config

#### Invitation Acceptance
- `src/app/verify/user_to_workspace/page.tsx` — Workspace invitation handler

---

## Rule 3: After Code Changes — Update Docs

When you make code changes that affect documented behavior, update the relevant doc file. Specifically update if you:

1. **Add/remove/rename a prop** → Update the props interface in the doc
2. **Add/remove a useEffect** → Update the effects list
3. **Add/remove a handler function** → Update the handlers section
4. **Change state structure** → Update the state/atoms section
5. **Change an API endpoint or payload** → Update the API/service section
6. **Add a new component** → Add to the component tree and file index
7. **Change status codes or enum values** → Update key concepts section
8. **Add a new route** → Update the Quick Lookup Table above

**Do NOT update docs for:** CSS-only changes, import reordering, variable renames within a function, comment changes.

---

## Rule 4: Debugging Workflow

When debugging an issue:

1. Identify which feature the bug is in (use the Quick Lookup Table above)
2. Read the relevant doc — understand the full flow
3. Read ONLY the specific source file where the bug likely lives
4. Fix the bug
5. If the fix changes documented behavior, update the doc

---

## Rule 5: New Feature Implementation Workflow

When implementing a new feature:

1. Check if a doc exists for the related feature area
2. If yes — read the "How to Extend" section in the doc
3. Follow the step-by-step file modification list
4. Read only the files you need to modify
5. After implementation, update the doc with new additions

---

## Rule 6: Cross-Feature Changes

Some changes span multiple features. Common cross-cutting concerns:

| Change | Docs to check |
|--------|--------------|
| New auth route or cookie | `docs/AUTH_FLOW_DOCUMENTATION.md` |
| New shared component | `docs/shared-components.md` |
| New API service | Relevant feature doc (service layer section) |
| New Jotai atom | Relevant feature doc (atoms section) |
| New dashboard route | Quick Lookup Table above + `src/middleware.ts` public paths |
| Theme/design changes | `docs/design.md` |
| New settings tab/section | `docs/features/settings-page.md` |
| Member/invitation changes | `docs/features/settings-page.md` |

---

## Rule 7: Adding New Documentation

When creating a new feature doc:

1. Use the `generate-feature-docs` skill (at `.claude/skills/generate-feature-docs/`)
2. Place the file in the correct location:
   - `docs/` — Top-level feature docs (auth, layout)
   - `docs/features/` — Feature/page-specific docs (agents, settings, call-history)
3. Update this file (`docs/RULES.md`):
   - Add to Quick Lookup Table
   - Add to Detailed Feature Mapping
   - Remove from Undocumented Features section
   - Update Documentation Stats
4. Update `CLAUDE.md` if the doc is referenced in project instructions

---

## Documentation Stats

| Doc | Lines | Source Files | Est. Tokens |
|-----|-------|-------------|-------------|
| `docs/AUTH_FLOW_DOCUMENTATION.md` | 1,629 | 21 files (~47KB) | ~8K |
| `docs/shared-components.md` | 908 | 29 files (~154KB) | ~5K |
| `docs/features/settings-page.md` | 601 | 11 files (~48KB) | ~3K |
| `docs/design.md` | 246 | — | ~1.5K |
| **Total documented** | **3,384** | **~61 files (~249KB)** | **~17.5K** |

### Coverage Gap

| Undocumented Feature | Source Size | Priority |
|---------------------|------------|----------|
| Agents (CRUD, form, providers) | ~130KB (14 files) | **High** — most complex feature |
| Call History (logs, filters, detail) | ~39KB (5 files) | Medium |
| Layout & Navigation (sidebar, menus) | ~30KB (10 files) | Low |
| Home / Dashboard | ~5KB (1 file) | Low |
| Phone Numbers | ~5KB (1 file) | Low — feature in progress |

**Current coverage:** ~55 files documented out of ~85 total (~65% by file count, ~53% by source size)

# Impacted Routes Report

> Generated: 2026-03-05T06:58:23.123850+00:00
> Comparing: `1b43a354` → `266a036c`
> Branch: `claude/shadcn-migration`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 0 |
| Transitively impacted routes | 10 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **10** |
| Files changed | 9 |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | `Logo.tsx` | Logo.tsx → index.tsx → page.tsx |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | `Logo.tsx` | Logo.tsx → ContainerComponent.tsx → page.tsx |
| `/auth/verify_signup` | `src/app/auth/verify_signup/page.tsx` | `Logo.tsx` | Logo.tsx → ContainerComponent.tsx → page.tsx |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | `Logo.tsx` | Logo.tsx → ContainerComponent.tsx → page.tsx |
| `/auth/login` | `src/app/auth/login/page.tsx` | `Logo.tsx` | Logo.tsx → index.tsx → LoginPage.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `Logo.tsx` | Logo.tsx → index.tsx → AgentListPage.tsx → page.tsx |
| `/auth/signup` | `src/app/auth/signup/page.tsx` | `Logo.tsx` | Logo.tsx → ContainerComponent.tsx → SignupClient.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/components/agents/AgentFormPage.tsx` | component | modified | +3 | -0 |
| `src/components/agents/agent-form/DynamicProviderFields.tsx` | component | added | +391 | -0 |
| `src/components/agents/agent-form/GeneralTab.tsx` | component | modified | +19 | -2 |
| `src/components/agents/agent-form/VoiceTab.tsx` | component | modified | +35 | -3 |
| `src/components/agents/agent-form/types.ts` | component | modified | +3 | -0 |
| `src/components/shared/Logo.tsx` | component | modified | +2 | -12 |
| `src/types/agent.ts` | type | modified | +3 | -0 |
| `src/types/provider.ts` | type | modified | +21 | -0 |
| `src/utils/agentFormUtils.ts` | util | modified | +9 | -0 |

---

## Dependency Chains

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/Logo.tsx (component, modified)
  → Logo.tsx  → ContainerComponent.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

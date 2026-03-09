# Impacted Routes Report

> Generated: 2026-03-09T13:06:58.328031+00:00
> Comparing: `1059ec54` → `d2b2110f`
> Branch: `claude/UI-improvements`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 2 |
| Transitively impacted routes | 7 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **9** |
| Files changed | 21 |

---

## Directly Modified Routes

Routes where `page.tsx` itself was changed.

| Route | File | Change |
|-------|------|--------|
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | modified |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | modified |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/auth/login` | `src/app/auth/login/page.tsx` | `LoginPage.tsx` | LoginPage.tsx → page.tsx |
| `/auth/signup` | `src/app/auth/signup/page.tsx` | `SignupClient.tsx` | SignupClient.tsx → page.tsx |
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `AgentListPage.tsx` | AgentListPage.tsx → page.tsx |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | `CustomTable.tsx` | CustomTable.tsx → index.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +17 | -8 |
| `src/app/auth/signup/SignupClient.tsx` | app-config | modified | +23 | -17 |
| `src/components/agents/AgentFormPage.tsx` | component | modified | +31 | -1 |
| `src/components/agents/AgentListPage.tsx` | component | modified | +1 | -1 |
| `src/components/agents/agent-form/DynamicProviderFields.tsx` | component | modified | +171 | -76 |
| `src/components/agents/agent-form/GeneralTab.tsx` | component | modified | +46 | -10 |
| `src/components/agents/agent-form/VoiceTab.tsx` | component | modified | +9 | -8 |
| `src/components/shared/CustomTable.tsx` | component | modified | +2 | -2 |
| `src/components/shared/FormCheckboxField.tsx` | component | added | +45 | -0 |
| `src/components/shared/FormRadioGroupField.tsx` | component | added | +45 | -0 |
| `src/components/shared/FormSelectInput.tsx` | component | added | +45 | -0 |
| `src/components/shared/FormTextAreaField.tsx` | component | added | +46 | -0 |
| `src/components/shared/FormTextInput.tsx` | component | added | +46 | -0 |
| `src/components/shared/TextInput.tsx` | component | modified | +2 | -2 |
| `src/components/shared/index.tsx` | component | modified | +15 | -0 |
| `src/components/ui/table.tsx` | component | modified | +1 | -1 |
| `src/schemas/auth.ts` | other | added | +39 | -0 |
| `src/app/auth/forgotpassword/page.tsx` | page | modified | +21 | -16 |
| `src/app/auth/reset-password/page.tsx` | page | modified | +29 | -27 |
| `src/types/provider.ts` | type | modified | +2 | -0 |
| `src/utils/validators.ts` | util | added | +68 | -0 |

---

## Dependency Chains

```
src/app/auth/login/LoginPage.tsx (app-config, modified)
  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/app/auth/signup/SignupClient.tsx (app-config, modified)
  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentListPage.tsx (component, modified)
  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, modified)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, modified)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, modified)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, modified)
  → CustomTable.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/FormCheckboxField.tsx (component, added)
  → FormCheckboxField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/FormRadioGroupField.tsx (component, added)
  → FormRadioGroupField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/FormSelectInput.tsx (component, added)
  → FormSelectInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/FormTextAreaField.tsx (component, added)
  → FormTextAreaField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/FormTextInput.tsx (component, added)
  → FormTextInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → FormTextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → FormTextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → FormTextInput.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/index.tsx (component, modified)
  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/table.tsx (component, modified)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/validators.ts (util, added)
  → validators.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/validators.ts (util, added)
  → validators.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/validators.ts (util, added)
  → validators.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

# Impacted Routes Report

> Generated: 2026-03-10T06:10:51.722267+00:00
> Comparing: `7e2039f9` → `c6b49195`
> Branch: `claude/UI-improvements`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 2 |
| Transitively impacted routes | 7 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **9** |
| Files changed | 20 |

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
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | `DynamicProviderFields.tsx` | DynamicProviderFields.tsx → AgentFormPage.tsx → page.tsx |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | `DynamicProviderFields.tsx` | DynamicProviderFields.tsx → AgentFormPage.tsx → page.tsx |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `DynamicProviderFields.tsx` | DynamicProviderFields.tsx → AgentFormPage.tsx → page.tsx |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | `CheckboxField.tsx` | CheckboxField.tsx → index.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `CheckboxField.tsx` | CheckboxField.tsx → index.tsx → AgentListPage.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +3 | -3 |
| `src/app/auth/signup/SignupClient.tsx` | app-config | modified | +4 | -4 |
| `src/components/agents/agent-form/DynamicProviderFields.tsx` | component | modified | +25 | -144 |
| `src/components/agents/agent-form/GeneralTab.tsx` | component | modified | +2 | -8 |
| `src/components/shared/CheckboxField.tsx` | component | modified | +40 | -11 |
| `src/components/shared/FormCheckboxField.tsx` | component | deleted | +0 | -45 |
| `src/components/shared/FormRadioGroupField.tsx` | component | deleted | +0 | -45 |
| `src/components/shared/FormSelectInput.tsx` | component | deleted | +0 | -45 |
| `src/components/shared/FormTextAreaField.tsx` | component | deleted | +0 | -46 |
| `src/components/shared/FormTextInput.tsx` | component | deleted | +0 | -46 |
| `src/components/shared/MultiSelectField.tsx` | component | added | +184 | -0 |
| `src/components/shared/RadioGroupField.tsx` | component | modified | +49 | -18 |
| `src/components/shared/SelectInput.tsx` | component | modified | +40 | -24 |
| `src/components/shared/SliderField.tsx` | component | added | +119 | -0 |
| `src/components/shared/TextAreaField.tsx` | component | modified | +40 | -9 |
| `src/components/shared/TextInput.tsx` | component | modified | +40 | -11 |
| `src/components/shared/index.tsx` | component | modified | +20 | -17 |
| `src/app/auth/forgotpassword/page.tsx` | page | modified | +2 | -2 |
| `src/app/auth/reset-password/page.tsx` | page | modified | +3 | -3 |
| `src/types/components.ts` | type | modified | +183 | -0 |

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
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, modified)
  → CheckboxField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, modified)
  → RadioGroupField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, modified)
  → SelectInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, modified)
  → TextAreaField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → SignupClient.tsx  → page.tsx
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

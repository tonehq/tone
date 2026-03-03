# Impacted Routes Report

> Generated: 2026-03-03T03:35:40.754619+00:00
> Comparing: `4e5e833b` → `8e8ea050`
> Branch: `claude/shadcn-migration`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 10 |
| Transitively impacted routes | 1 |
| Layout-impacted routes | 3 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **14** |
| Files changed | 100 |

---

## Directly Modified Routes

Routes where `page.tsx` itself was changed.

| Route | File | Change |
|-------|------|--------|
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | modified |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | modified |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | modified |
| `/home` | `src/app/(dashboard)/home/page.tsx` | modified |
| `/phone-numbers` | `src/app/(dashboard)/phone-numbers/page.tsx` | modified |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | modified |
| `/auth/check-email` | `src/app/auth/check-email/page.tsx` | modified |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | modified |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | modified |
| `/auth/verify_signup` | `src/app/auth/verify_signup/page.tsx` | renamed |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `AgentsAtom.tsx` | AgentsAtom.tsx → AgentListPage.tsx → page.tsx |

---

## Layout Changes

These layout files changed — all their child routes inherit the change.

| Layout File | URL Scope | Child Routes |
|-------------|-----------|--------------|
| `src/app/(dashboard)/layout.tsx` | `/` | `/`, `/auth/check-email`, `/auth/forgotpassword`, `/auth/signup`, `/auth/reset-password`, `/auth/verify_signup`, `/auth/login`, `/settings` (+6 more) |
| `src/app/layout.tsx` | `/` | `/`, `/auth/check-email`, `/auth/forgotpassword`, `/auth/signup`, `/auth/reset-password`, `/auth/verify_signup`, `/auth/login`, `/settings` (+6 more) |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +37 | -86 |
| `src/app/auth/shared/ContainerComponent.tsx` | app-config | modified | +122 | -208 |
| `src/app/auth/signup/SignupClient.tsx` | app-config | modified | +9 | -20 |
| `src/atoms/AgentsAtom.tsx` | atom | modified | +16 | -44 |
| `src/atoms/IntegrationAtom.tsx` | atom | added | +55 | -0 |
| `src/atoms/ProviderAtom.tsx` | atom | added | +20 | -0 |
| `src/components/agents/AgentActionMenu.tsx` | component | added | +22 | -0 |
| `src/components/agents/AgentFormPage.tsx` | component | added | +481 | -0 |
| `src/components/agents/AgentListPage.tsx` | component | modified | +95 | -144 |
| `src/components/agents/AgentTypeBadge.tsx` | component | added | +33 | -0 |
| `src/components/agents/AssignPhoneNumberModal.tsx` | component | added | +145 | -0 |
| `src/components/agents/CreateAgentModal.tsx` | component | modified | +33 | -127 |
| `src/components/agents/agent-form/CallConfigurationTab.tsx` | component | modified | +19 | -32 |
| `src/components/agents/agent-form/GeneralTab.tsx` | component | modified | +92 | -118 |
| `src/components/agents/agent-form/VoiceTab.tsx` | component | modified | +169 | -243 |
| `src/components/agents/agent-form/promptPage.tsx` | component | modified | +84 | -83 |
| `src/components/agents/agent-form/types.ts` | component | modified | +3 | -3 |
| `src/components/icons/google.tsx` | component | added | +28 | -0 |
| `src/components/settings/AddChannelModal.tsx` | component | added | +123 | -0 |
| `src/components/settings/ApiKeysTab.tsx` | component | added | +147 | -0 |
| `src/components/settings/Apikeys.tsx` | component | added | +51 | -0 |
| `src/components/settings/Integrations.tsx` | component | added | +119 | -0 |
| `src/components/settings/IntegrationsTable.tsx` | component | added | +114 | -0 |
| `src/components/settings/PublicKeysTab.tsx` | component | added | +256 | -0 |
| `src/components/settings/constants.tsx` | component | added | +28 | -0 |
| `src/components/shared/ActionMenu.tsx` | component | added | +80 | -0 |
| `src/components/shared/CheckboxField.tsx` | component | added | +87 | -0 |
| `src/components/shared/CustomButton.tsx` | component | modified | +62 | -109 |
| `src/components/shared/CustomLink.tsx` | component | added | +31 | -0 |
| `src/components/shared/CustomModal.tsx` | component | added | +101 | -0 |
| `src/components/shared/CustomTab.tsx` | component | added | +82 | -0 |
| `src/components/shared/CustomTable.tsx` | component | added | +351 | -0 |
| `src/components/shared/Divider.tsx` | component | added | +12 | -0 |
| `src/components/shared/Form.tsx` | component | renamed | +0 | -0 |
| `src/components/shared/Logo.tsx` | component | added | +66 | -0 |
| `src/components/shared/MainLayout.tsx` | component | added | +74 | -0 |
| `src/components/shared/RadioGroupField.tsx` | component | added | +138 | -0 |
| `src/components/shared/SelectInput.tsx` | component | added | +126 | -0 |
| `src/components/shared/SidebarComponent/SidebarContent.tsx` | component | added | +48 | -0 |
| `src/components/shared/SidebarComponent/SidebarHeader.tsx` | component | added | +56 | -0 |
| `src/components/shared/SidebarComponent/SidebarItemMenu.tsx` | component | added | +45 | -0 |
| `src/components/shared/SidebarComponent/SidebarNav.tsx` | component | added | +59 | -0 |
| `src/components/shared/SidebarComponent/SidebarOrganization.tsx` | component | added | +51 | -0 |
| `src/components/shared/SidebarComponent/constant.tsx` | component | deleted | +0 | -28 |
| `src/components/shared/SidebarComponent/index.tsx` | component | modified | +40 | -265 |
| `src/components/shared/TextAreaField.tsx` | component | added | +94 | -0 |
| `src/components/shared/TextInput.tsx` | component | modified | +80 | -126 |
| `src/components/shared/index.tsx` | component | added | +43 | -0 |
| `src/components/shared/userMenu.tsx` | component | modified | +78 | -189 |
| `src/components/ui/badge.tsx` | component | added | +46 | -0 |
| `src/components/ui/button.tsx` | component | added | +62 | -0 |
| `src/components/ui/card.tsx` | component | added | +75 | -0 |
| `src/components/ui/checkbox.tsx` | component | added | +29 | -0 |
| `src/components/ui/dialog.tsx` | component | added | +144 | -0 |
| `src/components/ui/dropdown-menu.tsx` | component | added | +228 | -0 |
| `src/components/ui/input.tsx` | component | added | +20 | -0 |
| `src/components/ui/label.tsx` | component | added | +21 | -0 |
| `src/components/ui/radio-group.tsx` | component | added | +48 | -0 |
| `src/components/ui/select.tsx` | component | added | +175 | -0 |
| `src/components/ui/separator.tsx` | component | added | +28 | -0 |
| `src/components/ui/sheet.tsx` | component | added | +134 | -0 |
| `src/components/ui/slider.tsx` | component | added | +58 | -0 |
| `src/components/ui/switch.tsx` | component | added | +35 | -0 |
| `src/components/ui/table.tsx` | component | added | +92 | -0 |
| `src/components/ui/tabs.tsx` | component | added | +81 | -0 |
| `src/components/ui/textarea.tsx` | component | added | +18 | -0 |
| `src/components/ui/tooltip.tsx` | component | added | +53 | -0 |
| `src/constants/index.ts` | config | modified | +2 | -0 |
| `src/constants/sidebar.ts` | config | added | +28 | -0 |
| `src/constants/theme.ts` | config | added | +82 | -0 |
| `src/urls.ts` | config | deleted | +0 | -1 |
| `src/hooks/useMediaQuery.ts` | hook | added | +18 | -0 |
| `src/app/(dashboard)/layout.tsx` | layout | modified | +3 | -30 |
| `src/app/layout.tsx` | layout | modified | +19 | -5 |
| `src/app/(dashboard)/agents/create/inbound/page.tsx` | page | modified | +2 | -276 |
| `src/app/(dashboard)/agents/create/outbound/page.tsx` | page | modified | +2 | -243 |
| `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | page | modified | +3 | -309 |
| `src/app/(dashboard)/home/page.tsx` | page | modified | +234 | -144 |
| `src/app/(dashboard)/phone-numbers/page.tsx` | page | modified | +12 | -124 |
| `src/app/(dashboard)/settings/page.tsx` | page | modified | +95 | -221 |
| `src/app/auth/check-email/page.tsx` | page | modified | +3 | -3 |
| `src/app/auth/forgotpassword/page.tsx` | page | modified | +7 | -14 |
| `src/app/auth/reset-password/page.tsx` | page | modified | +4 | -8 |
| `src/app/auth/verify_signup/page.tsx` | page | renamed | +0 | -0 |
| `src/services/agentsService.ts` | service | modified | +4 | -0 |
| `src/services/auth/helper.tsx` | service | modified | +0 | -2 |
| `src/services/channelService.ts` | service | added | +33 | -0 |
| `src/services/phoneNumberService.ts` | service | added | +34 | -0 |
| `src/services/providerService.ts` | service | added | +9 | -0 |
| `src/services/shared/helper.tsx` | service | deleted | +0 | -166 |
| `src/types/agent.ts` | type | modified | +67 | -5 |
| `src/types/components.ts` | type | added | +53 | -0 |
| `src/types/integration.ts` | type | added | +7 | -0 |
| `src/types/provider.ts` | type | added | +20 | -0 |
| `src/types/sidebar.ts` | type | added | +13 | -0 |
| `src/utils/agentFormUtils.ts` | util | renamed | +0 | -0 |
| `src/utils/axios.ts` | util | modified | +1 | -1 |
| `src/utils/cn.ts` | util | added | +6 | -0 |
| `src/utils/helpers.ts` | util | added | +10 | -0 |
| `src/utils/theme.ts` | util | modified | +16 | -16 |

---

## Dependency Chains

```
src/atoms/AgentsAtom.tsx (atom, modified)
  → AgentsAtom.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/atoms/IntegrationAtom.tsx (atom, added)
  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/atoms/ProviderAtom.tsx (atom, added)
  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/atoms/ProviderAtom.tsx (atom, added)
  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/atoms/ProviderAtom.tsx (atom, added)
  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/AgentActionMenu.tsx (component, added)
  → AgentActionMenu.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, added)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, added)
  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, added)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/AgentListPage.tsx (component, modified)
  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/AgentTypeBadge.tsx (component, added)
  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentTypeBadge.tsx (component, added)
  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentTypeBadge.tsx (component, added)
  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/AgentTypeBadge.tsx (component, added)
  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/AssignPhoneNumberModal.tsx (component, added)
  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AssignPhoneNumberModal.tsx (component, added)
  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AssignPhoneNumberModal.tsx (component, added)
  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/CreateAgentModal.tsx (component, modified)
  → CreateAgentModal.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/agent-form/promptPage.tsx (component, modified)
  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/promptPage.tsx (component, modified)
  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/promptPage.tsx (component, modified)
  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/settings/Apikeys.tsx (component, added)
  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/Integrations.tsx (component, added)
  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/card.tsx (component, added)
  → card.tsx  → page.tsx
  → /home  [src/app/(dashboard)/home/page.tsx]
```

```
src/components/ui/card.tsx (component, added)
  → card.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/card.tsx (component, added)
  → card.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/card.tsx (component, added)
  → card.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/switch.tsx (component, added)
  → switch.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/tabs.tsx (component, added)
  → tabs.tsx  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → agentsService.ts  → AgentsAtom.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentsAtom.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/services/channelService.ts (service, added)
  → channelService.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/services/phoneNumberService.ts (service, added)
  → phoneNumberService.ts  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/services/phoneNumberService.ts (service, added)
  → phoneNumberService.ts  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/services/phoneNumberService.ts (service, added)
  → phoneNumberService.ts  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/services/providerService.ts (service, added)
  → providerService.ts  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/services/providerService.ts (service, added)
  → providerService.ts  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/services/providerService.ts (service, added)
  → providerService.ts  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, renamed)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, renamed)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, renamed)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → agentsService.ts  → AgentsAtom.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → page.tsx
  → /home  [src/app/(dashboard)/home/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → switch.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

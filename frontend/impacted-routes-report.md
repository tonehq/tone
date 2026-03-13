# Impacted Routes Report

> Generated: 2026-03-11T17:43:44.655938+00:00
> Comparing: `5c85922e` → `7ca54923`
> Branch: `parandhama_dev`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 13 |
| Transitively impacted routes | 3 |
| Layout-impacted routes | 1 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **17** |
| Files changed | 126 |

---

## Directly Modified Routes

Routes where `page.tsx` itself was changed.

| Route | File | Change |
|-------|------|--------|
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | modified |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | modified |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | modified |
| `/home` | `src/app/(dashboard)/home/page.tsx` | modified |
| `/members` | `src/app/(dashboard)/members/page.tsx` | added |
| `/phone-numbers` | `src/app/(dashboard)/phone-numbers/page.tsx` | modified |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | modified |
| `/auth/check-email` | `src/app/auth/check-email/page.tsx` | modified |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | modified |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | modified |
| `/auth/verify-signup` | `src/app/auth/verify-signup/page.tsx` | deleted |
| `/auth/verify_signup` | `src/app/auth/verify_signup/page.tsx` | added |
| `/verify/user_to_workspace` | `src/app/verify/user_to_workspace/page.tsx` | added |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/auth/login` | `src/app/auth/login/page.tsx` | `LoginPage.tsx` | LoginPage.tsx → page.tsx |
| `/auth/signup` | `src/app/auth/signup/page.tsx` | `ContainerComponent.tsx` | ContainerComponent.tsx → SignupClient.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `AgentsAtom.tsx` | AgentsAtom.tsx → AgentListPage.tsx → page.tsx |

---

## Layout Changes

These layout files changed — all their child routes inherit the change.

| Layout File | URL Scope | Child Routes |
|-------------|-----------|--------------|
| `src/app/(dashboard)/layout.tsx` | `/` | `/`, `/verify/user_to_workspace`, `/auth/check-email`, `/auth/forgotpassword`, `/auth/signup`, `/auth/reset-password`, `/auth/verify_signup`, `/auth/login` (+8 more) |
| `src/app/layout.tsx` | `/` | `/`, `/verify/user_to_workspace`, `/auth/check-email`, `/auth/forgotpassword`, `/auth/signup`, `/auth/reset-password`, `/auth/verify_signup`, `/auth/login` (+8 more) |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +54 | -96 |
| `src/app/auth/shared/ContainerComponent.tsx` | app-config | modified | +122 | -208 |
| `src/app/auth/signup/SignupClient.tsx` | app-config | modified | +45 | -82 |
| `src/atoms/AgentsAtom.tsx` | atom | modified | +16 | -44 |
| `src/atoms/IntegrationAtom.tsx` | atom | added | +52 | -0 |
| `src/atoms/ProviderAtom.tsx` | atom | added | +20 | -0 |
| `src/atoms/SettingsAtom.tsx` | atom | modified | +16 | -35 |
| `src/components/ThemeRegistry.tsx` | component | deleted | +0 | -13 |
| `src/components/agents/AgentActionMenu.tsx` | component | added | +22 | -0 |
| `src/components/agents/AgentFormPage.tsx` | component | added | +495 | -0 |
| `src/components/agents/AgentListPage.tsx` | component | modified | +93 | -145 |
| `src/components/agents/AgentTypeBadge.tsx` | component | added | +33 | -0 |
| `src/components/agents/AssignPhoneNumberModal.tsx` | component | added | +145 | -0 |
| `src/components/agents/CreateAgentModal.tsx` | component | modified | +33 | -127 |
| `src/components/agents/agent-form/CallConfigurationTab.tsx` | component | modified | +43 | -40 |
| `src/components/agents/agent-form/DynamicProviderFields.tsx` | component | added | +414 | -0 |
| `src/components/agents/agent-form/GeneralTab.tsx` | component | modified | +315 | -174 |
| `src/components/agents/agent-form/VoiceSelect.tsx` | component | added | +150 | -0 |
| `src/components/agents/agent-form/VoiceTab.tsx` | component | modified | +337 | -235 |
| `src/components/agents/agent-form/promptPage.tsx` | component | modified | +98 | -111 |
| `src/components/agents/agent-form/types.ts` | component | modified | +6 | -3 |
| `src/components/icons/google.tsx` | component | added | +28 | -0 |
| `src/components/settings/AddChannelModal.tsx` | component | added | +123 | -0 |
| `src/components/settings/ApiKeysTab.tsx` | component | added | +145 | -0 |
| `src/components/settings/Apikeys.tsx` | component | modified | +42 | -622 |
| `src/components/settings/Integrations.tsx` | component | added | +115 | -0 |
| `src/components/settings/IntegrationsTable.tsx` | component | added | +114 | -0 |
| `src/components/settings/InvitationsTable.tsx` | component | added | +118 | -0 |
| `src/components/settings/InviteMemberModal.tsx` | component | added | +168 | -0 |
| `src/components/settings/Members.tsx` | component | added | +135 | -0 |
| `src/components/settings/MembersTable.tsx` | component | added | +168 | -0 |
| `src/components/settings/PublicKeysTab.tsx` | component | added | +257 | -0 |
| `src/components/settings/SidebarComponent.tsx` | component | deleted | +0 | -44 |
| `src/components/settings/constants.tsx` | component | modified | +7 | -7 |
| `src/components/shared/ActionMenu.tsx` | component | added | +80 | -0 |
| `src/components/shared/CheckboxField.tsx` | component | added | +116 | -0 |
| `src/components/shared/CustomButton.tsx` | component | modified | +62 | -109 |
| `src/components/shared/CustomLink.tsx` | component | added | +31 | -0 |
| `src/components/shared/CustomModal.tsx` | component | added | +101 | -0 |
| `src/components/shared/CustomTab.tsx` | component | added | +82 | -0 |
| `src/components/shared/CustomTable.tsx` | component | added | +260 | -0 |
| `src/components/shared/Divider.tsx` | component | added | +12 | -0 |
| `src/components/shared/Form.tsx` | component | renamed | +0 | -0 |
| `src/components/shared/Logo.tsx` | component | added | +56 | -0 |
| `src/components/shared/MainLayout.tsx` | component | added | +74 | -0 |
| `src/components/shared/MultiSelectField.tsx` | component | added | +184 | -0 |
| `src/components/shared/RadioGroupField.tsx` | component | added | +169 | -0 |
| `src/components/shared/SearchableSelect.tsx` | component | added | +258 | -0 |
| `src/components/shared/SelectInput.tsx` | component | added | +144 | -0 |
| `src/components/shared/SidebarComponent/SidebarContent.tsx` | component | added | +48 | -0 |
| `src/components/shared/SidebarComponent/SidebarHeader.tsx` | component | added | +56 | -0 |
| `src/components/shared/SidebarComponent/SidebarItemMenu.tsx` | component | added | +45 | -0 |
| `src/components/shared/SidebarComponent/SidebarNav.tsx` | component | added | +59 | -0 |
| `src/components/shared/SidebarComponent/SidebarOrganization.tsx` | component | added | +51 | -0 |
| `src/components/shared/SidebarComponent/constant.tsx` | component | deleted | +0 | -28 |
| `src/components/shared/SidebarComponent/index.tsx` | component | modified | +40 | -268 |
| `src/components/shared/SliderField.tsx` | component | added | +119 | -0 |
| `src/components/shared/TextAreaField.tsx` | component | added | +125 | -0 |
| `src/components/shared/TextInput.tsx` | component | modified | +117 | -134 |
| `src/components/shared/index.tsx` | component | added | +64 | -0 |
| `src/components/shared/userMenu.tsx` | component | modified | +78 | -199 |
| `src/components/ui/badge.tsx` | component | added | +46 | -0 |
| `src/components/ui/button.tsx` | component | added | +62 | -0 |
| `src/components/ui/card.tsx` | component | added | +75 | -0 |
| `src/components/ui/checkbox.tsx` | component | added | +29 | -0 |
| `src/components/ui/dialog.tsx` | component | added | +144 | -0 |
| `src/components/ui/dropdown-menu.tsx` | component | added | +228 | -0 |
| `src/components/ui/input.tsx` | component | added | +20 | -0 |
| `src/components/ui/label.tsx` | component | added | +21 | -0 |
| `src/components/ui/popover.tsx` | component | added | +42 | -0 |
| `src/components/ui/radio-group.tsx` | component | added | +48 | -0 |
| `src/components/ui/select.tsx` | component | added | +175 | -0 |
| `src/components/ui/separator.tsx` | component | added | +28 | -0 |
| `src/components/ui/sheet.tsx` | component | added | +134 | -0 |
| `src/components/ui/slider.tsx` | component | added | +62 | -0 |
| `src/components/ui/sonner.tsx` | component | added | +36 | -0 |
| `src/components/ui/switch.tsx` | component | added | +35 | -0 |
| `src/components/ui/table.tsx` | component | added | +270 | -0 |
| `src/components/ui/tabs.tsx` | component | added | +81 | -0 |
| `src/components/ui/textarea.tsx` | component | added | +18 | -0 |
| `src/components/ui/tooltip.tsx` | component | added | +53 | -0 |
| `src/constants/index.ts` | config | modified | +2 | -0 |
| `src/constants/sidebar.ts` | config | added | +31 | -0 |
| `src/constants/theme.ts` | config | added | +82 | -0 |
| `src/urls.ts` | config | deleted | +0 | -1 |
| `src/hooks/useMediaQuery.ts` | hook | added | +18 | -0 |
| `src/app/(dashboard)/layout.tsx` | layout | modified | +3 | -30 |
| `src/app/layout.tsx` | layout | modified | +15 | -5 |
| `src/schemas/auth.ts` | other | added | +39 | -0 |
| `src/app/(dashboard)/agents/create/inbound/page.tsx` | page | modified | +2 | -276 |
| `src/app/(dashboard)/agents/create/outbound/page.tsx` | page | modified | +2 | -243 |
| `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | page | modified | +3 | -309 |
| `src/app/(dashboard)/home/page.tsx` | page | modified | +234 | -144 |
| `src/app/(dashboard)/members/page.tsx` | page | added | +11 | -0 |
| `src/app/(dashboard)/phone-numbers/page.tsx` | page | modified | +12 | -130 |
| `src/app/(dashboard)/settings/page.tsx` | page | modified | +4 | -222 |
| `src/app/auth/check-email/page.tsx` | page | modified | +18 | -65 |
| `src/app/auth/forgotpassword/page.tsx` | page | modified | +34 | -52 |
| `src/app/auth/reset-password/page.tsx` | page | modified | +37 | -57 |
| `src/app/auth/verify-signup/page.tsx` | page | deleted | +0 | -92 |
| `src/app/auth/verify_signup/page.tsx` | page | added | +69 | -0 |
| `src/app/verify/user_to_workspace/page.tsx` | page | added | +164 | -0 |
| `src/services/agentsService.ts` | service | modified | +4 | -0 |
| `src/services/auth/helper.tsx` | service | modified | +3 | -4 |
| `src/services/channelService.ts` | service | added | +33 | -0 |
| `src/services/phoneNumberService.ts` | service | added | +34 | -0 |
| `src/services/providerService.ts` | service | added | +9 | -0 |
| `src/services/shared/helper.tsx` | service | deleted | +0 | -166 |
| `src/services/userService.ts` | service | modified | +32 | -4 |
| `src/services/voiceService.ts` | service | added | +38 | -0 |
| `src/types/agent.ts` | type | modified | +70 | -5 |
| `src/types/components.ts` | type | added | +236 | -0 |
| `src/types/integration.ts` | type | added | +7 | -0 |
| `src/types/provider.ts` | type | added | +44 | -0 |
| `src/types/settings/members.ts` | type | modified | +16 | -13 |
| `src/types/sidebar.ts` | type | added | +13 | -0 |
| `src/utils/agentFormUtils.ts` | util | renamed | +0 | -0 |
| `src/utils/axios.ts` | util | modified | +1 | -1 |
| `src/utils/cn.ts` | util | added | +6 | -0 |
| `src/utils/date.ts` | util | added | +17 | -0 |
| `src/utils/helpers.ts` | util | added | +23 | -0 |
| `src/utils/notification.tsx` | util | deleted | +0 | -58 |
| `src/utils/selectUtils.ts` | util | added | +44 | -0 |
| `src/utils/theme.ts` | util | deleted | +0 | -242 |
| `src/utils/toast.tsx` | util | added | +15 | -0 |
| `src/utils/validators.ts` | util | added | +68 | -0 |

---

## Dependency Chains

```
src/app/auth/login/LoginPage.tsx (app-config, modified)
  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/app/auth/shared/ContainerComponent.tsx (app-config, modified)
  → ContainerComponent.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/app/auth/signup/SignupClient.tsx (app-config, modified)
  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

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
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/atoms/ProviderAtom.tsx (atom, added)
  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/atoms/ProviderAtom.tsx (atom, added)
  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/atoms/SettingsAtom.tsx (atom, modified)
  → SettingsAtom.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/agents/AgentActionMenu.tsx (component, added)
  → AgentActionMenu.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
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
src/components/agents/AgentFormPage.tsx (component, added)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentListPage.tsx (component, modified)
  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
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
  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentTypeBadge.tsx (component, added)
  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
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
src/components/agents/AssignPhoneNumberModal.tsx (component, added)
  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/CreateAgentModal.tsx (component, modified)
  → CreateAgentModal.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/agents/agent-form/CallConfigurationTab.tsx (component, modified)
  → CallConfigurationTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/CallConfigurationTab.tsx (component, modified)
  → CallConfigurationTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/CallConfigurationTab.tsx (component, modified)
  → CallConfigurationTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/DynamicProviderFields.tsx (component, added)
  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/GeneralTab.tsx (component, modified)
  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
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
src/components/agents/agent-form/VoiceSelect.tsx (component, added)
  → VoiceSelect.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/VoiceSelect.tsx (component, added)
  → VoiceSelect.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceSelect.tsx (component, added)
  → VoiceSelect.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/VoiceTab.tsx (component, modified)
  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
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
src/components/agents/agent-form/promptPage.tsx (component, modified)
  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/agent-form/types.ts (component, modified)
  → types.ts  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/icons/google.tsx (component, added)
  → google.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/settings/AddChannelModal.tsx (component, added)
  → AddChannelModal.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/Integrations.tsx (component, added)
  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/IntegrationsTable.tsx (component, added)
  → IntegrationsTable.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/InvitationsTable.tsx (component, added)
  → InvitationsTable.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/settings/InviteMemberModal.tsx (component, added)
  → InviteMemberModal.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/settings/Members.tsx (component, added)
  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/settings/MembersTable.tsx (component, added)
  → MembersTable.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/ActionMenu.tsx (component, added)
  → ActionMenu.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CheckboxField.tsx (component, added)
  → CheckboxField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → page.tsx
  → /phone-numbers  [src/app/(dashboard)/phone-numbers/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CustomButton.tsx (component, modified)
  → CustomButton.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CustomLink.tsx (component, added)
  → CustomLink.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CustomModal.tsx (component, added)
  → CustomModal.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/CustomTab.tsx (component, added)
  → CustomTab.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → IntegrationsTable.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → InvitationsTable.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/CustomTable.tsx (component, added)
  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/Divider.tsx (component, added)
  → Divider.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/Form.tsx (component, renamed)
  → Form.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → ContainerComponent.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/Logo.tsx (component, added)
  → Logo.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/MultiSelectField.tsx (component, added)
  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
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
  → MultiSelectField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/RadioGroupField.tsx (component, added)
  → RadioGroupField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/SearchableSelect.tsx (component, added)
  → SearchableSelect.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/SelectInput.tsx (component, added)
  → SelectInput.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/SliderField.tsx (component, added)
  → SliderField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
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
  → SliderField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/TextAreaField.tsx (component, added)
  → TextAreaField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
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
  → TextInput.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/shared/TextInput.tsx (component, modified)
  → TextInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
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
  → TextInput.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
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
  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/shared/index.tsx (component, added)
  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → InvitationsTable.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
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
  → badge.tsx  → AgentTypeBadge.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/badge.tsx (component, added)
  → badge.tsx  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → page.tsx
  → /phone-numbers  [src/app/(dashboard)/phone-numbers/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/button.tsx (component, added)
  → button.tsx  → CustomButton.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/card.tsx (component, added)
  → card.tsx  → page.tsx
  → /home  [src/app/(dashboard)/home/page.tsx]
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
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → MultiSelectField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → MultiSelectField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → MultiSelectField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/checkbox.tsx (component, added)
  → checkbox.tsx  → MultiSelectField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/dialog.tsx (component, added)
  → dialog.tsx  → CustomModal.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → TextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → TextInput.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → TextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → TextInput.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/input.tsx (component, added)
  → input.tsx  → MultiSelectField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → TextInput.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → TextInput.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → TextInput.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → TextInput.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/label.tsx (component, added)
  → label.tsx  → SearchableSelect.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/popover.tsx (component, added)
  → popover.tsx  → SearchableSelect.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/radio-group.tsx (component, added)
  → radio-group.tsx  → RadioGroupField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/select.tsx (component, added)
  → select.tsx  → SelectInput.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
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
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → promptPage.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → Divider.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → Divider.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → Divider.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/separator.tsx (component, added)
  → separator.tsx  → Divider.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → SliderField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → SliderField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → SliderField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/slider.tsx (component, added)
  → slider.tsx  → SliderField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/switch.tsx (component, added)
  → switch.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/switch.tsx (component, added)
  → switch.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/switch.tsx (component, added)
  → switch.tsx  → GeneralTab.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → IntegrationsTable.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → InvitationsTable.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/table.tsx (component, added)
  → table.tsx  → CustomTable.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/ui/textarea.tsx (component, added)
  → textarea.tsx  → TextAreaField.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → helper.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → helper.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → helper.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → userService.ts  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
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
  → index.ts  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → userService.ts  → SettingsAtom.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/constants/index.ts (config, modified)
  → index.ts  → axios.ts  → channelService.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
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
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/services/agentsService.ts (service, modified)
  → agentsService.ts  → AgentsAtom.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/services/auth/helper.tsx (service, modified)
  → helper.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/services/auth/helper.tsx (service, modified)
  → helper.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/services/auth/helper.tsx (service, modified)
  → helper.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/services/channelService.ts (service, added)
  → channelService.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
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
src/services/phoneNumberService.ts (service, added)
  → phoneNumberService.ts  → AssignPhoneNumberModal.tsx  → AgentFormPage.tsx  → page.tsx
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
src/services/providerService.ts (service, added)
  → providerService.ts  → ProviderAtom.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/services/userService.ts (service, modified)
  → userService.ts  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/services/userService.ts (service, modified)
  → userService.ts  → SettingsAtom.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/services/voiceService.ts (service, added)
  → voiceService.ts  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/services/voiceService.ts (service, added)
  → voiceService.ts  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/services/voiceService.ts (service, added)
  → voiceService.ts  → VoiceTab.tsx  → index.ts  → AgentFormPage.tsx  → page.tsx
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
src/utils/agentFormUtils.ts (util, renamed)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → userService.ts  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
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
  → axios.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → helper.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → helper.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → userService.ts  → SettingsAtom.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/utils/axios.ts (util, modified)
  → axios.ts  → channelService.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
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
  → cn.ts  → CustomButton.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → CustomButton.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → CustomButton.tsx  → page.tsx
  → /phone-numbers  [src/app/(dashboard)/phone-numbers/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → CustomButton.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → CustomButton.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
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
  → cn.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → google.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → CustomButton.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → AgentTypeBadge.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → SearchableSelect.tsx  → index.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/utils/cn.ts (util, added)
  → cn.ts  → SearchableSelect.tsx  → index.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/date.ts (util, added)
  → date.ts  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/date.ts (util, added)
  → date.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/helpers.ts (util, added)
  → helpers.ts  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/utils/selectUtils.ts (util, added)
  → selectUtils.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/selectUtils.ts (util, added)
  → selectUtils.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/selectUtils.ts (util, added)
  → selectUtils.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → page.tsx
  → /auth/forgotpassword  [src/app/auth/forgotpassword/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → page.tsx
  → /verify/user_to_workspace  [src/app/verify/user_to_workspace/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → page.tsx
  → /auth/verify_signup  [src/app/auth/verify_signup/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → page.tsx
  → /auth/reset-password  [src/app/auth/reset-password/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → Members.tsx  → page.tsx
  → /members  [src/app/(dashboard)/members/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/toast.tsx (util, added)
  → toast.tsx  → SignupClient.tsx  → page.tsx
  → /auth/signup  [src/app/auth/signup/page.tsx]
```

```
src/utils/validators.ts (util, added)
  → validators.ts  → DynamicProviderFields.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
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

import type { StepperStep } from '@/components/shared';

export const ONBOARDING_STEP_KEYS = ['workspace', 'invites', 'use_case', 'industry'] as const;

export type OnboardingStepKey = (typeof ONBOARDING_STEP_KEYS)[number];

export const ONBOARDING_STEPS: readonly (StepperStep & { key: OnboardingStepKey })[] = [
  { key: 'workspace', title: 'Workspace' },
  { key: 'invites', title: 'Invite teammates' },
  { key: 'use_case', title: 'Use case' },
  { key: 'industry', title: 'Industry' },
];

export const SKIPPABLE_STEPS: readonly OnboardingStepKey[] = ['invites', 'industry'];

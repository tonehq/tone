import type { UseFormReturn } from 'react-hook-form';

export interface OnboardingInviteRow {
  email: string;
  role: string;
}

export interface OnboardingFormValues {
  workspace_name: string;
  invites: OnboardingInviteRow[];
  use_case: string;
  industry: string;
}

export type OnboardingForm = UseFormReturn<OnboardingFormValues>;

'use client';

import { OnboardingWizard, useOnboardingWizard } from '@/components/onboarding';

export default function OnboardingPage() {
  const wizard = useOnboardingWizard();
  return <OnboardingWizard wizard={wizard} />;
}

'use client';

import { SelectInput } from '@/components/shared';
import { INDUSTRY_OPTIONS } from '@/constants/onboarding';

import type { OnboardingForm } from '../types';

interface IndustryStepProps {
  form: OnboardingForm;
}

export default function IndustryStep({ form }: IndustryStepProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Which industry are you in?</h1>
        <p className="text-sm text-muted-foreground">
          Pick the closest match. You can leave this blank if you&apos;d rather not say.
        </p>
      </div>
      <SelectInput
        name="industry"
        control={form.control}
        label="Industry"
        placeholder="Select an industry"
        options={INDUSTRY_OPTIONS}
      />
    </div>
  );
}

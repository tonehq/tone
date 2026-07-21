'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { useCompleteOnboarding } from '@/lib/api/auth';
import { handleApiError, showToast } from '@/lib/toast';
import { onboardingSchema, type OnboardingFormData } from '@/schemas/auth';
import { useAuthStore } from '@/stores/auth';

import { ONBOARDING_STEPS, type OnboardingStepKey } from './constants';

export interface UseOnboardingWizardResult {
  form: ReturnType<typeof useForm<OnboardingFormData>>;
  stepIndex: number;
  activeStepKey: OnboardingStepKey;
  isFirstStep: boolean;
  isLastStep: boolean;
  submitting: boolean;
  next: () => Promise<void>;
  back: () => void;
  skip: () => Promise<void>;
  finish: () => Promise<void>;
}

// Per-step gate: which form fields must be RHF-valid before we advance.
// Skippable steps (`invites`, `industry`) have no gate — the user can hit Skip
// or Continue on an untouched step and we move on.
const STEP_GATE: Record<OnboardingStepKey, ReadonlyArray<keyof OnboardingFormData>> = {
  workspace: ['workspace_name'],
  invites: ['invites'],
  use_case: ['use_case'],
  industry: [],
};

/**
 * Owns the wizard's step index + form state + submit lifecycle. Step
 * components are pure presentational — they read `form` via the wizard
 * context and never touch step transitions themselves. Keeps the page
 * component ~15 lines.
 */
export function useOnboardingWizard(): UseOnboardingWizardResult {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const organization = useAuthStore((s) => s.organization);
  const setOrganization = useAuthStore((s) => s.setOrganization);
  const completeOnboarding = useCompleteOnboarding();
  const [stepIndex, setStepIndex] = useState(0);
  const workspacePrefilledRef = useRef(false);

  const form = useForm<OnboardingFormData>({
    resolver: zodResolver(onboardingSchema),
    mode: 'onTouched',
    defaultValues: {
      workspace_name: '',
      invites: [{ email: '', role: 'developer' }],
      use_case: '',
      industry: '',
    },
  });

  // Prefill workspace name from first_name once the auth store lands.
  // Guarded by a ref so clearing the field doesn't re-populate it.
  useEffect(() => {
    if (workspacePrefilledRef.current) return;
    if (!user) return;
    workspacePrefilledRef.current = true;
    const first = (user.first_name || '').trim();
    form.setValue('workspace_name', first ? `${first}'s Workspace` : 'My Workspace');
  }, [user, form]);

  // Bail out early if the user has already onboarded (e.g. deep link).
  useEffect(() => {
    if (organization?.onboarding_completed) {
      router.replace('/home');
    }
  }, [organization?.onboarding_completed, router]);

  const activeStepKey = ONBOARDING_STEPS[stepIndex].key;
  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === ONBOARDING_STEPS.length - 1;

  const submit = useCallback(async () => {
    // Full-form validation before the network call, regardless of which step
    // we're on. Any lingering error routes the user back to that step's data
    // instead of surfacing a 400 from the server.
    const ok = await form.trigger();
    if (!ok) return;
    const values = form.getValues();
    const cleanedInvites = values.invites
      .map((row) => ({ email: row.email.trim(), role: row.role }))
      .filter((row) => row.email.length > 0);
    try {
      const result = await completeOnboarding.mutateAsync({
        workspace_name: values.workspace_name.trim(),
        use_case: values.use_case,
        industry: values.industry ? values.industry : null,
        invites: cleanedInvites,
      });
      setOrganization({
        ...(organization ?? { id: result.organization.id, name: result.organization.name }),
        ...result.organization,
      });
      const invited = result.invites_sent.length;
      const failed = result.invites_failed.length;
      showToast.success(
        'Workspace ready!',
        invited || failed
          ? `${invited} invite${invited === 1 ? '' : 's'} sent${failed ? `, ${failed} failed` : ''}.`
          : 'Taking you to your dashboard.',
      );
      router.push('/home');
    } catch (err) {
      handleApiError(err);
    }
  }, [completeOnboarding, form, organization, router, setOrganization]);

  const next = useCallback(async () => {
    const fields = STEP_GATE[activeStepKey];
    if (fields.length) {
      const ok = await form.trigger(fields as (keyof OnboardingFormData)[]);
      if (!ok) return;
    }
    if (isLastStep) {
      await submit();
      return;
    }
    setStepIndex((i) => i + 1);
  }, [activeStepKey, form, isLastStep, submit]);

  const back = useCallback(() => {
    setStepIndex((i) => Math.max(0, i - 1));
  }, []);

  const skip = useCallback(async () => {
    // Skip step 2 (invites): clear the list so no invites are sent.
    // Skip step 4 (industry): clear industry and finalize.
    if (activeStepKey === 'invites') {
      form.setValue('invites', [{ email: '', role: 'developer' }]);
      setStepIndex((i) => i + 1);
      return;
    }
    if (activeStepKey === 'industry') {
      form.setValue('industry', '');
      await submit();
    }
  }, [activeStepKey, form, submit]);

  const finish = useCallback(() => submit(), [submit]);

  return useMemo(
    () => ({
      form,
      stepIndex,
      activeStepKey,
      isFirstStep,
      isLastStep,
      submitting: completeOnboarding.isPending,
      next,
      back,
      skip,
      finish,
    }),
    [
      form,
      stepIndex,
      activeStepKey,
      isFirstStep,
      isLastStep,
      completeOnboarding.isPending,
      next,
      back,
      skip,
      finish,
    ],
  );
}

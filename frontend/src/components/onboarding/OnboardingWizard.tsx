'use client';

import { motion } from 'framer-motion';

import { CustomButton, Stepper } from '@/components/shared';

import { ONBOARDING_STEPS, SKIPPABLE_STEPS } from './constants';
import IndustryStep from './steps/IndustryStep';
import InvitesStep from './steps/InvitesStep';
import UseCaseStep from './steps/UseCaseStep';
import WorkspaceStep from './steps/WorkspaceStep';
import type { UseOnboardingWizardResult } from './useOnboardingWizard';

interface OnboardingWizardProps {
  wizard: UseOnboardingWizardResult;
}

/**
 * Presentational shell: renders the stepper header, the active step, and the
 * shared nav footer. All state lives in `useOnboardingWizard`; this component
 * owns no state of its own so it stays trivial to snapshot-test.
 */
export default function OnboardingWizard({ wizard }: OnboardingWizardProps) {
  const { form, stepIndex, activeStepKey, isFirstStep, isLastStep, submitting, next, back, skip } =
    wizard;
  const canSkip = SKIPPABLE_STEPS.includes(activeStepKey);

  return (
    <motion.div
      key={activeStepKey}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-8"
    >
      <Stepper steps={[...ONBOARDING_STEPS]} currentIndex={stepIndex} />

      {activeStepKey === 'workspace' && <WorkspaceStep form={form} />}
      {activeStepKey === 'invites' && <InvitesStep form={form} />}
      {activeStepKey === 'use_case' && <UseCaseStep form={form} />}
      {activeStepKey === 'industry' && <IndustryStep form={form} />}

      <div className="flex items-center justify-between pt-2">
        <CustomButton type="text" onClick={back} disabled={isFirstStep || submitting}>
          Back
        </CustomButton>
        <div className="flex items-center gap-2">
          {canSkip && (
            <CustomButton type="text" onClick={skip} disabled={submitting}>
              {activeStepKey === 'invites' ? 'Skip for now' : 'Skip'}
            </CustomButton>
          )}
          <CustomButton type="primary" onClick={next} disabled={submitting} loading={submitting}>
            {isLastStep ? 'Finish' : 'Continue'}
          </CustomButton>
        </div>
      </div>
    </motion.div>
  );
}

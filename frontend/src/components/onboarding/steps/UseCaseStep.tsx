'use client';

import { Controller } from 'react-hook-form';

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { USE_CASE_OPTIONS } from '@/constants/onboarding';
import { cn } from '@/utils/cn';

import type { OnboardingForm } from '../types';

interface UseCaseStepProps {
  form: OnboardingForm;
}

/**
 * Card-style radio group. Uses the shadcn RadioGroup primitive directly so the
 * cards get real radio ARIA semantics (role, keyboard navigation) while looking
 * like clickable tiles instead of plain radios. This is a domain-specific
 * composition — see the shared-components rule exception in CLAUDE.md.
 */
export default function UseCaseStep({ form }: UseCaseStepProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          What are you planning to use Tone for?
        </h1>
        <p className="text-sm text-muted-foreground">
          This helps us tailor examples and templates to your goals.
        </p>
      </div>
      <Controller
        control={form.control}
        name="use_case"
        render={({ field }) => (
          <RadioGroup
            value={field.value}
            onValueChange={field.onChange}
            className="grid grid-cols-1 gap-3 sm:grid-cols-2"
          >
            {USE_CASE_OPTIONS.map((option) => {
              const selected = field.value === option.value;
              return (
                <label
                  key={option.value}
                  htmlFor={`use-case-${option.value}`}
                  className={cn(
                    'cursor-pointer rounded-lg border p-4 text-left transition-colors',
                    'hover:border-primary/50 hover:bg-primary/[0.03]',
                    selected
                      ? 'border-primary bg-primary/[0.06] ring-1 ring-primary'
                      : 'border-border bg-background',
                  )}
                >
                  <RadioGroupItem
                    id={`use-case-${option.value}`}
                    value={option.value}
                    className="sr-only"
                  />
                  <div className="text-sm font-medium">{option.label}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{option.description}</div>
                </label>
              );
            })}
          </RadioGroup>
        )}
      />
    </div>
  );
}

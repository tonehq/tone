'use client';

import { Check } from 'lucide-react';

import { cn } from '@/utils/cn';

export interface StepperStep {
  key: string;
  title: string;
}

interface StepperProps {
  steps: StepperStep[];
  currentIndex: number;
  className?: string;
}

export default function Stepper({ steps, currentIndex, className }: StepperProps) {
  return (
    <ol className={cn('flex w-full items-center gap-2', className)}>
      {steps.map((step, i) => {
        const isDone = i < currentIndex;
        const isActive = i === currentIndex;
        return (
          <li
            key={step.key}
            className="flex flex-1 items-center gap-2"
            aria-current={isActive ? 'step' : undefined}
          >
            <div
              className={cn(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium transition-colors',
                isDone && 'border-primary bg-primary text-primary-foreground',
                isActive && 'border-primary bg-primary/10 text-primary',
                !isDone && !isActive && 'border-muted-foreground/30 text-muted-foreground',
              )}
            >
              {isDone ? <Check className="h-4 w-4" /> : i + 1}
            </div>
            <span
              className={cn(
                'hidden text-sm font-medium sm:inline',
                isDone && 'text-foreground',
                isActive && 'text-foreground',
                !isDone && !isActive && 'text-muted-foreground',
              )}
            >
              {step.title}
            </span>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  'h-px flex-1',
                  i < currentIndex ? 'bg-primary' : 'bg-muted-foreground/20',
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

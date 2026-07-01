'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Plus, PhoneForwarded, Sparkles, Workflow } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';
import WorkflowPathwayIllustration from './WorkflowPathwayIllustration';

interface Props {
  onCreate: () => void;
}

const FEATURES = [
  { icon: GitBranch, label: 'Branch on caller intent' },
  { icon: PhoneForwarded, label: 'Call tools & transfer' },
  { icon: Workflow, label: 'Reuse across agents' },
];

const WorkflowEmptyState: React.FC<Props> = ({ onCreate }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3, ease: 'easeOut' }}
    className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-b from-muted/40 to-transparent"
  >
    {/* soft radial glow */}
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-48 opacity-70"
      style={{
        background:
          'radial-gradient(60% 100% at 50% 0%, hsl(var(--primary) / 0.10), transparent 70%)',
      }}
    />
    <div className="relative flex flex-col items-center px-6 py-16 text-center">
      <WorkflowPathwayIllustration />

      <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
        <Sparkles className="h-3 w-3 text-primary" />
        Visual conversation builder
      </div>

      <h2 className="mt-4 text-xl font-semibold tracking-tight text-foreground">
        Design your first workflow
      </h2>
      <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
        Map out a branching conversation on a visual canvas — greet, collect details, call tools,
        transfer, and end — then assign it to any agent.
      </p>

      <CustomButton
        type="primary"
        className="mt-6"
        icon={<Plus className="h-4 w-4" />}
        onClick={onCreate}
      >
        New workflow
      </CustomButton>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        {FEATURES.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
          >
            <Icon className="h-3.5 w-3.5 text-primary/70" />
            {label}
          </span>
        ))}
      </div>
    </div>
  </motion.div>
);

export default WorkflowEmptyState;

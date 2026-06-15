'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Plus, PhoneForwarded, Sparkles, Workflow } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';

interface Props {
  onCreate: () => void;
}

/** A small stylised "pathway" diagram used in the empty state. */
const PathwayIllustration: React.FC = () => (
  <svg
    width="300"
    height="150"
    viewBox="0 0 300 150"
    fill="none"
    className="text-border"
    aria-hidden
  >
    {/* connectors */}
    <path d="M150 38 C150 58, 96 58, 96 80" stroke="currentColor" strokeWidth="1.5" fill="none" />
    <path
      d="M150 38 C150 58, 204 58, 204 80"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeDasharray="5 4"
      fill="none"
    />
    <path
      d="M96 110 C96 128, 150 128, 150 128"
      stroke="currentColor"
      strokeWidth="1.5"
      fill="none"
    />
    <path
      d="M204 110 C204 128, 150 128, 150 128"
      stroke="currentColor"
      strokeWidth="1.5"
      fill="none"
    />

    {/* start node (indigo) */}
    <g>
      <rect
        x="108"
        y="14"
        width="84"
        height="26"
        rx="8"
        className="fill-card"
        stroke="hsl(var(--border))"
      />
      <rect x="108" y="14" width="84" height="2.5" rx="1.25" fill="#6366f1" />
      <circle cx="120" cy="27" r="3.5" fill="#10b981" />
      <rect x="130" y="22" width="46" height="4" rx="2" className="fill-muted-foreground/40" />
    </g>
    {/* decision (amber) */}
    <g>
      <rect
        x="58"
        y="80"
        width="76"
        height="30"
        rx="8"
        className="fill-card"
        stroke="hsl(var(--border))"
      />
      <rect x="58" y="80" width="76" height="2.5" rx="1.25" fill="#f59e0b" />
      <circle cx="70" cy="95" r="3.5" fill="#f59e0b" />
      <rect x="80" y="90" width="40" height="4" rx="2" className="fill-muted-foreground/40" />
    </g>
    {/* tool (violet) */}
    <g>
      <rect
        x="166"
        y="80"
        width="76"
        height="30"
        rx="8"
        className="fill-card"
        stroke="hsl(var(--border))"
      />
      <rect x="166" y="80" width="76" height="2.5" rx="1.25" fill="#8b5cf6" />
      <circle cx="178" cy="95" r="3.5" fill="#8b5cf6" />
      <rect x="188" y="90" width="40" height="4" rx="2" className="fill-muted-foreground/40" />
    </g>
    {/* end (rose) */}
    <g>
      <rect
        x="112"
        y="126"
        width="76"
        height="22"
        rx="8"
        className="fill-card"
        stroke="hsl(var(--border))"
      />
      <circle cx="124" cy="137" r="3.5" fill="#f43f5e" />
      <rect x="134" y="135" width="40" height="4" rx="2" className="fill-muted-foreground/40" />
    </g>
  </svg>
);

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
      <PathwayIllustration />

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

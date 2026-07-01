'use client';

import React from 'react';

/** A small stylised "pathway" diagram used in the workflows empty state. */
const WorkflowPathwayIllustration: React.FC = () => (
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

export default WorkflowPathwayIllustration;

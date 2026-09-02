import React from 'react';

/** Small uppercase section label used across the node/edge config forms. */
const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
    {children}
  </div>
);

export default SectionTitle;

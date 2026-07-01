'use client';

import React from 'react';

interface ApiRequestEmptyHintProps {
  children: React.ReactNode;
}

const ApiRequestEmptyHint: React.FC<ApiRequestEmptyHintProps> = ({ children }) => (
  <p className="rounded-md border border-dashed border-border px-3 py-2 text-center text-xs text-muted-foreground">
    {children}
  </p>
);

export default ApiRequestEmptyHint;

import React from 'react';

import { cn } from '@/utils/cn';

/** Bordered surface used to group fields inside the node/edge config forms. */
const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className={cn('rounded-lg border border-border bg-muted/30 p-3', className)}>{children}</div>
);

export default Card;

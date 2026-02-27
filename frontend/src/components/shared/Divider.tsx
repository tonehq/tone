'use client';

import { Separator } from '@/components/ui/separator';
import { cn } from '@/utils/cn';

type DividerProps = React.ComponentProps<typeof Separator>;

const Divider = ({ className, orientation = 'horizontal', ...props }: DividerProps) => (
  <Separator orientation={orientation} className={cn(className)} {...props} />
);

export default Divider;

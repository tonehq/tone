'use client';

import React from 'react';
import { Trash2 } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';

interface ApiRequestRemoveButtonProps {
  onClick: () => void;
  label: string;
}

const ApiRequestRemoveButton: React.FC<ApiRequestRemoveButtonProps> = ({ onClick, label }) => (
  <CustomButton
    type="text"
    size="icon-sm"
    aria-label={label}
    onClick={onClick}
    className="mt-1 shrink-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
    icon={<Trash2 className="h-4 w-4" />}
  />
);

export default ApiRequestRemoveButton;

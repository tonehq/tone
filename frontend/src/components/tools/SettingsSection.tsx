'use client';

import CustomButton from '@/components/shared/CustomButton';
import { cn } from '@/utils/cn';
import { ChevronDown } from 'lucide-react';

interface SettingsSectionProps {
  title: string;
  description: string;
  icon: React.ElementType;
  iconColor?: string;
  iconBg?: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

export default function SettingsSection({
  title,
  description,
  icon: Icon,
  iconColor,
  iconBg,
  isOpen,
  onToggle,
  children,
}: SettingsSectionProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-background shadow-sm transition-shadow">
      <CustomButton
        type="text"
        fullWidth
        onClick={onToggle}
        className="!h-auto flex !justify-start items-center gap-3.5 px-5 py-4 text-left transition-colors hover:bg-muted/30"
      >
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-xl',
            iconBg ?? 'bg-muted',
          )}
        >
          <Icon size={20} className={iconColor ?? 'text-muted-foreground'} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        </div>
        <div
          className={cn(
            'flex size-7 shrink-0 items-center justify-center rounded-md transition-all duration-200 cursor-pointer',
            isOpen ? 'rotate-180 bg-muted' : 'rotate-0',
          )}
        >
          <ChevronDown size={15} className="text-muted-foreground" />
        </div>
      </CustomButton>
      <div
        className={cn(
          'grid transition-all duration-200 ease-in-out',
          isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border/50 px-5 py-5">{children}</div>
        </div>
      </div>
    </div>
  );
}

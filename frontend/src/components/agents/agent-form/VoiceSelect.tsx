'use client';

import SearchableSelect, {
  type SearchableSelectOption,
} from '@/components/shared/SearchableSelect';
import { Badge } from '@/components/ui/badge';
import type { VoiceItem } from '@/services/voiceService';
import { CheckIcon } from 'lucide-react';
import React, { useCallback, useMemo } from 'react';

interface VoiceSelectOption extends SearchableSelectOption {
  name: string;
  gender: string;
  accent: string;
  description: string;
}

interface VoiceSelectProps {
  name: string;
  voices: VoiceItem[];
  value?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
}

const GRADIENT_PAIRS = [
  'from-violet-500 to-purple-600',
  'from-blue-500 to-cyan-500',
  'from-emerald-500 to-teal-500',
  'from-orange-400 to-amber-500',
  'from-pink-500 to-rose-400',
  'from-indigo-500 to-blue-500',
  'from-fuchsia-500 to-pink-500',
  'from-cyan-500 to-sky-500',
  'from-lime-500 to-green-500',
  'from-red-400 to-orange-500',
];

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function VoiceAvatar({ name, size = 32 }: { name: string; size?: number }) {
  const gradient = GRADIENT_PAIRS[hashString(name) % GRADIENT_PAIRS.length];
  const initial = name.charAt(0).toUpperCase();
  return (
    <div
      className={`bg-gradient-to-br ${gradient} flex shrink-0 items-center justify-center rounded-full font-semibold text-white shadow-sm`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initial}
    </div>
  );
}

function VoiceSelect({
  name,
  voices,
  value,
  onValueChange,
  placeholder = 'Select a voice',
  loading = false,
  disabled = false,
}: VoiceSelectProps) {
  const options: VoiceSelectOption[] = useMemo(
    () =>
      voices.map((v) => ({
        value: v.voice_id,
        label: v.name,
        name: v.name,
        gender: v.gender,
        accent: v.accent,
        description: v.description,
      })),
    [voices],
  );

  const filterFn = useCallback((option: VoiceSelectOption, query: string): boolean => {
    const q = query.toLowerCase();
    return (
      option.name.toLowerCase().includes(q) ||
      option.gender.toLowerCase().includes(q) ||
      option.accent.toLowerCase().includes(q) ||
      option.description.toLowerCase().includes(q)
    );
  }, []);

  const renderOption = useCallback(
    (option: VoiceSelectOption, isSelected: boolean) => (
      <div className="flex w-full items-center gap-3 py-0.5">
        <VoiceAvatar name={option.name} size={40} />
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-semibold leading-tight text-foreground">
            {option.name}
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            {option.gender && (
              <Badge
                variant="outline"
                className="h-[18px] rounded-full px-1.5 py-0 text-[10px] font-medium capitalize text-muted-foreground"
              >
                {option.gender}
              </Badge>
            )}
            {option.description && (
              <span className="truncate text-[11px] leading-tight text-muted-foreground/80">
                {option.description}
              </span>
            )}
          </div>
        </div>
        {isSelected && <CheckIcon className="size-4 shrink-0 text-primary" />}
      </div>
    ),
    [],
  );

  const renderSelectedValue = useCallback(
    (option: VoiceSelectOption) => (
      <span className="flex items-center gap-2">
        <VoiceAvatar name={option.name} size={22} />
        <span className="truncate text-sm font-medium">{option.name}</span>
      </span>
    ),
    [],
  );

  return (
    <SearchableSelect<VoiceSelectOption>
      name={name}
      options={options}
      value={value}
      onValueChange={onValueChange}
      placeholder={placeholder}
      searchPlaceholder="Search voices..."
      loading={loading}
      disabled={disabled}
      filterFn={filterFn}
      renderOption={renderOption}
      renderSelectedValue={renderSelectedValue}
      emptyMessage="No voices found."
    />
  );
}

export default React.memo(VoiceSelect);

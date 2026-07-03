'use client';

import { Mic, Pause, Play, Volume2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import DynamicProviderFields from '@/components/agents/agent-form/DynamicProviderFields';
import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import {
  CustomButton,
  SearchableSelect,
  SelectInput,
  SliderField,
  type SearchableSelectOption,
} from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listProviderCatalog, listProviderModels } from '@/services/servicesService';
import type { ProviderCatalogItem, ProviderModel } from '@/types/service';
import {
  listTtsLanguages,
  listTtsProviders,
  listTtsVoices,
  type TtsLanguage,
  type TtsProvider,
  type TtsVoice,
} from '@/services/ttsService';
import type { AgentFormState } from '@/types/agent';
import type { MetaDataSchemaField } from '@/types/provider';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

/** Keys in voice_settings / stt_settings that are structural (not schema fields). */
const TTS_STRUCTURAL_KEYS = new Set([
  'provider_id',
  'model_id',
  'model',
  'voice_id',
  'language',
  'language_code',
  'speed',
]);
const STT_STRUCTURAL_KEYS = new Set(['provider_id', 'model_id', 'model']);

export default function VoiceStep() {
  const { control, setValue, getValues, reset } = useFormContext<AgentFormState>();
  const voiceSettings = useWatch({ control, name: 'config.voice_settings' });
  // STT provider lives on config.stt_settings.provider_id. RHF accepts the
  // dotted path; we cast `name` to `never` to satisfy the strongly-typed
  // useWatch signature without inflating AgentFormState.
  const sttProviderId = useWatch({
    control,
    name: 'config.stt_settings.provider_id' as never,
  }) as string | null | undefined;
  const sttModel = useWatch({
    control,
    name: 'config.stt_settings.model' as never,
  }) as string | null | undefined;
  const ttsModelId = useWatch({
    control,
    name: 'config.voice_settings.model_id' as never,
  }) as string | null | undefined;

  const [languages, setLanguages] = useState<TtsLanguage[]>([]);
  const [providers, setProviders] = useState<TtsProvider[]>([]);
  const [voices, setVoices] = useState<TtsVoice[]>([]);
  const [sttProviders, setSttProviders] = useState<ProviderCatalogItem[]>([]);
  const [sttModels, setSttModels] = useState<ProviderModel[]>([]);
  const [ttsModels, setTtsModels] = useState<ProviderModel[]>([]);
  const [loadingLangs, setLoadingLangs] = useState(false);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingVoices, setLoadingVoices] = useState(false);
  const [loadingStt, setLoadingStt] = useState(false);
  const [loadingSttModels, setLoadingSttModels] = useState(false);
  const [loadingTtsModels, setLoadingTtsModels] = useState(false);
  const [nowPlaying, setNowPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // ─── stt provider catalog ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoadingStt(true);
    listProviderCatalog('stt')
      .then((items) => {
        if (cancelled) return;
        setSttProviders(items.filter((p) => p.kinds.includes('stt')));
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingStt(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ─── language load ────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoadingLangs(true);
    listTtsLanguages()
      .then((rows) => {
        if (cancelled) return;
        setLanguages(rows);

        // Backward compat: if saved language is a raw code (e.g. "en")
        // from an older agent, resolve it to the display name (e.g. "English").
        // Use reset so both _formValues AND _defaultValues update together —
        // setValue(.., shouldDirty:false) alone desyncs them and any later RHF
        // dirty recompute flips isDirty true even with no user edits.
        const saved = voiceSettings?.language;
        if (saved && !rows.some((l) => l.name === saved)) {
          const match = rows.find((l) => l.codes?.includes(saved));
          if (match) {
            const current = getValues();
            reset(
              {
                ...current,
                config: {
                  ...current.config,
                  voice_settings: { ...current.config.voice_settings, language: match.name },
                },
              },
              { keepDirty: true, keepDirtyValues: true },
            );
          }
        }
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingLangs(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ─── provider load (depends on language) ──────────────────────────────────
  const language = voiceSettings?.language ?? '';
  useEffect(() => {
    if (!language) {
      setProviders([]);
      return;
    }
    let cancelled = false;
    setLoadingProviders(true);
    listTtsProviders(language)
      .then((rows) => {
        if (!cancelled) setProviders(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingProviders(false);
      });
    return () => {
      cancelled = true;
    };
  }, [language]);

  // ─── voices load (depends on provider + language + model) ──────────────────
  const providerId = voiceSettings?.provider_id ?? '';
  useEffect(() => {
    if (!providerId || !language) {
      setVoices([]);
      return;
    }
    let cancelled = false;
    setLoadingVoices(true);
    listTtsVoices(providerId, language, ttsModelId)
      .then((rows) => {
        if (!cancelled) setVoices(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingVoices(false);
      });
    return () => {
      cancelled = true;
    };
  }, [providerId, language, ttsModelId]);

  // ─── TTS models (depends on provider) ─────────────────────────────────────
  useEffect(() => {
    if (!providerId) {
      setTtsModels([]);
      return;
    }
    let cancelled = false;
    setLoadingTtsModels(true);
    listProviderModels(providerId, { service_type: 'tts', page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) setTtsModels(res.rows.filter((m) => m.is_active));
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingTtsModels(false);
      });
    return () => {
      cancelled = true;
    };
  }, [providerId]);

  // ─── STT models (depends on STT provider) ─────────────────────────────────
  useEffect(() => {
    if (!sttProviderId) {
      setSttModels([]);
      return;
    }
    let cancelled = false;
    setLoadingSttModels(true);
    listProviderModels(sttProviderId, { service_type: 'stt', page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) setSttModels(res.rows.filter((m) => m.is_active));
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingSttModels(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sttProviderId]);

  // ─── audio sample playback ────────────────────────────────────────────────
  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
    }
    setNowPlaying(null);
  }, []);

  const togglePlay = useCallback(
    (voice: TtsVoice) => {
      if (!voice.sample_url) return;
      if (nowPlaying === voice.id) {
        stopPlayback();
        return;
      }
      const el = audioRef.current ?? new Audio();
      audioRef.current = el;
      el.src = voice.sample_url;
      el.onended = () => setNowPlaying(null);
      el.play()
        .then(() => setNowPlaying(voice.id))
        .catch(() => setNowPlaying(null));
    },
    [nowPlaying, stopPlayback],
  );

  useEffect(() => () => stopPlayback(), [stopPlayback]);

  // ─── selection ────────────────────────────────────────────────────────────
  const setLanguage = (v: string) => {
    setValue('config.voice_settings.language', v || null, { shouldDirty: true });
    setValue('config.voice_settings.language_code' as never, null as never, { shouldDirty: true });
    setValue('config.voice_settings.provider_id', null, { shouldDirty: true });
    setValue('config.voice_settings.model_id' as never, null as never, { shouldDirty: true });
    setValue('config.voice_settings.voice_id', null, { shouldDirty: true });
  };
  const setProvider = (v: string) => {
    setValue('config.voice_settings.provider_id', v || null, { shouldDirty: true });
    setValue('config.voice_settings.model_id' as never, null as never, { shouldDirty: true });
    setValue('config.voice_settings.voice_id', null, { shouldDirty: true });
    // Persist the provider-specific language code for runtime use
    const matched = providers.find((p) => p.id === v);
    if (matched?.language_code) {
      setValue('config.voice_settings.language_code' as never, matched.language_code as never, {
        shouldDirty: true,
      });
    }
  };

  const languageOptions = useMemo(
    () =>
      languages.map((l) => ({
        value: l.name,
        // Title-case so "english (gb)" → "English (Gb)" instead of shouting
        // ALL CAPS in the dropdown.
        label: l.name.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()),
      })),
    [languages],
  );
  const providerOptions = useMemo(
    () => providers.map((p) => ({ value: p.id, label: p.display_name })),
    [providers],
  );

  const selectedVoiceId = voiceSettings?.voice_id ?? '';
  const selectedVoice = voices.find((v) => v.id === selectedVoiceId);

  // ─── voice-picker options for SearchableSelect ────────────────────────────
  interface VoiceOption extends SearchableSelectOption {
    voice: TtsVoice;
  }
  const voiceOptions = useMemo<VoiceOption[]>(
    () =>
      voices.map((v) => {
        const desc = v.description ? ` — ${v.description}` : '';
        return {
          value: v.id,
          label: `${v.name}${desc}`,
          voice: v,
        };
      }),
    [voices],
  );

  // ─── meta_data_schema for TTS and STT ─────────────────────────────────────
  // Prefer model-level schema, fall back to provider-level
  const ttsSchema = useMemo<MetaDataSchemaField[]>(() => {
    if (ttsModelId) {
      const model = ttsModels.find((m) => m.id === ttsModelId);
      if (model?.meta_data_schema && model.meta_data_schema.length > 0) {
        return model.meta_data_schema;
      }
    }
    // Fallback: TTS provider returns meta_data_schema as a flat array
    if (!providerId) return [];
    const matched = providers.find((p) => p.id === providerId);
    return matched?.meta_data_schema ?? [];
  }, [ttsModelId, ttsModels, providerId, providers]);

  const sttSchema = useMemo<MetaDataSchemaField[]>(() => {
    if (sttModel) {
      // STT uses model name, not model_id — find by name in sttModels
      const model = sttModels.find((m) => m.name === sttModel || m.id === sttModel);
      if (model?.meta_data_schema && model.meta_data_schema.length > 0) {
        return model.meta_data_schema;
      }
    }
    // Fallback: provider catalog has meta_data_schema keyed by kind
    if (!sttProviderId) return [];
    const matched = sttProviders.find((p) => p.id === sttProviderId);
    return matched?.meta_data_schema?.stt ?? [];
  }, [sttModel, sttModels, sttProviderId, sttProviders]);

  // Clear stale TTS / STT schema field values when the user CHANGES the
  // model. Skipped on the initial settle so the saved settings aren't
  // silently mutated on load — see AiStep for the same rationale (silent
  // setValue with shouldDirty:false desyncs _formValues from _defaultValues
  // and later trips RHF's deep-equality isDirty check, causing a spurious
  // discard-changes prompt).
  const prevTtsAllowedKeysRef = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!ttsSchema.length) {
      prevTtsAllowedKeysRef.current = null;
      return;
    }
    const allowedKeys = new Set(ttsSchema.map((f) => f.name));
    const prev = prevTtsAllowedKeysRef.current;
    prevTtsAllowedKeysRef.current = allowedKeys;
    if (prev === null) return;
    if (prev.size === allowedKeys.size && [...prev].every((k) => allowedKeys.has(k))) return;

    const current = getValues('config.voice_settings' as never) as
      | Record<string, unknown>
      | undefined;
    if (!current) return;
    for (const key of Object.keys(current)) {
      if (!TTS_STRUCTURAL_KEYS.has(key) && !allowedKeys.has(key)) {
        setValue(`config.voice_settings.${key}` as never, undefined as never, {
          shouldDirty: true,
        });
      }
    }
  }, [ttsSchema]);

  const prevSttAllowedKeysRef = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!sttSchema.length) {
      prevSttAllowedKeysRef.current = null;
      return;
    }
    const allowedKeys = new Set(sttSchema.map((f) => f.name));
    const prev = prevSttAllowedKeysRef.current;
    prevSttAllowedKeysRef.current = allowedKeys;
    if (prev === null) return;
    if (prev.size === allowedKeys.size && [...prev].every((k) => allowedKeys.has(k))) return;

    const current = getValues('config.stt_settings' as never) as
      | Record<string, unknown>
      | undefined;
    if (!current) return;
    for (const key of Object.keys(current)) {
      if (!STT_STRUCTURAL_KEYS.has(key) && !allowedKeys.has(key)) {
        setValue(`config.stt_settings.${key}` as never, undefined as never, {
          shouldDirty: true,
        });
      }
    }
  }, [sttSchema]);

  // ─── render helpers ───────────────────────────────────────────────────────
  const showProviderField = !!language;
  const showModelField = !!providerId;
  const showVoiceField = !!providerId; // Model is optional, voice can come right after provider
  const showSpeedSlider = !!selectedVoiceId;

  return (
    <div className="flex flex-col gap-4">
      {/* ─── Text-to-Speech ─────────────────────────────────────────────── */}
      <SectionCard
        icon={<Volume2 className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.violet}
        title="Text-to-speech"
        description="Language, provider, and voice the agent uses to talk."
        action={
          voices.length > 0 ? (
            <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
              {voices.length} voices
            </Badge>
          ) : null
        }
      >
        {/* Step 1 — Language */}
        <SelectInput
          name="voice_language"
          label="Language"
          options={languageOptions}
          value={language}
          onValueChange={setLanguage}
          loading={loadingLangs}
          placeholder="Select a language"
        />

        {/* Step 2 — Provider (revealed after language is chosen) */}
        {showProviderField && (
          <SelectInput
            name="voice_provider"
            label="Provider"
            options={providerOptions}
            value={providerId}
            onValueChange={setProvider}
            loading={loadingProviders}
            placeholder="Select a provider"
          />
        )}

        {/* Step 3 — Model (revealed after provider is chosen) */}
        {showModelField && (
          <SelectInput
            name="voice_model"
            label="Model"
            options={ttsModels.map((m) => ({
              value: m.id,
              label: m.display_name || m.name,
            }))}
            value={ttsModelId ?? ''}
            onValueChange={(v) => {
              setValue('config.voice_settings.model_id' as never, (v || null) as never, {
                shouldDirty: true,
              });
              setValue('config.voice_settings.voice_id', null, { shouldDirty: true });
            }}
            loading={loadingTtsModels}
            placeholder="Select a model"
            helperText="Optional — the provider's default model is used when blank."
          />
        )}

        {/* Step 4 — Voice (searchable dropdown beside a play button) */}
        {showVoiceField && (
          <div className="flex flex-col gap-2">
            <div className="flex items-end gap-2">
              <div className="min-w-0 flex-1">
                <SearchableSelect<VoiceOption>
                  name="voice_id"
                  label="Voice"
                  options={voiceOptions}
                  value={selectedVoiceId}
                  onValueChange={(v) => {
                    setValue('config.voice_settings.voice_id', v, { shouldDirty: true });
                  }}
                  loading={loadingVoices}
                  placeholder="Search voices…"
                  searchPlaceholder="Search by name…"
                  emptyMessage="No voices match. Try another provider."
                  filterFn={(opt, q) => {
                    const v = opt.voice;
                    const hay = [v.name, v.description, v.gender, v.accent]
                      .filter(Boolean)
                      .join(' ')
                      .toLowerCase();
                    return hay.includes(q.toLowerCase());
                  }}
                  renderOption={(opt, isSelected) => (
                    <VoiceRow voice={opt.voice} isSelected={isSelected} />
                  )}
                  renderSelectedValue={(opt) => <VoiceRow voice={opt.voice} isSelected dense />}
                />
              </div>
              {selectedVoice?.sample_url && (
                <CustomButton
                  type="text"
                  size="icon"
                  onClick={() => togglePlay(selectedVoice)}
                  aria-label={
                    nowPlaying === selectedVoice.id ? 'Pause sample' : 'Play voice sample'
                  }
                  className={cn(
                    'size-9 shrink-0 rounded-full border transition-colors',
                    nowPlaying === selectedVoice.id
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border bg-background hover:bg-muted',
                  )}
                >
                  {nowPlaying === selectedVoice.id ? (
                    <Pause className="size-3.5" />
                  ) : (
                    <Play className="size-3.5" />
                  )}
                </CustomButton>
              )}
            </div>
          </div>
        )}

        {/* Step 5 — Provider-specific TTS settings */}
        {showVoiceField && ttsSchema.length > 0 && (
          <DynamicProviderFields
            fields={ttsSchema}
            basePath="config.voice_settings"
            exclude={['voice_id']}
          />
        )}
      </SectionCard>

      {/* ─── Speech-to-Text ─────────────────────────────────────────────── */}
      <SectionCard
        icon={<Mic className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.sky}
        title="Speech-to-text"
        description="How the agent transcribes caller speech."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectInput
            name="config.stt_settings.provider_id"
            label="Provider"
            options={sttProviders.map((p) => ({ value: p.id, label: p.display_name }))}
            loading={loadingStt}
            value={sttProviderId ?? ''}
            onValueChange={(v) => {
              setValue('config.stt_settings.provider_id' as never, (v || null) as never, {
                shouldDirty: true,
              });
              // Reset the model when the provider changes — names rarely
              // overlap across providers. model_id must go with it: leaving
              // the old provider's id behind makes the backend resolve the
              // wrong model row (and its base_url) on calls.
              setValue('config.stt_settings.model' as never, null as never, {
                shouldDirty: true,
              });
              setValue('config.stt_settings.model_id' as never, null as never, {
                shouldDirty: true,
              });
            }}
            placeholder="Select a provider"
          />
          <SelectInput
            name="config.stt_settings.model"
            label="Model"
            options={sttModels.map((m) => ({
              value: m.name,
              label: m.display_name || m.name,
            }))}
            loading={loadingSttModels}
            value={sttModel ?? ''}
            onValueChange={(v) => {
              setValue('config.stt_settings.model' as never, (v || null) as never, {
                shouldDirty: true,
              });
              // Keep model_id in lockstep with the selected model name so a
              // stale id from a previous provider can never be saved.
              const matched = sttModels.find((m) => m.name === v);
              setValue('config.stt_settings.model_id' as never, (matched?.id ?? null) as never, {
                shouldDirty: true,
              });
            }}
            disabled={!sttProviderId}
            placeholder={sttProviderId ? 'Select a model' : 'Pick a provider first'}
          />
        </div>
        {sttSchema.length > 0 && (
          <DynamicProviderFields fields={sttSchema} basePath="config.stt_settings" />
        )}
        <p className="text-[11px] text-muted-foreground">
          Caller speech is transcribed by this provider/model before reaching the LLM.
        </p>
      </SectionCard>
    </div>
  );
}

// ─── voice option row (avatar + name + description + gender) ────────────────
function VoiceRow({
  voice,
  isSelected,
  dense = false,
}: {
  voice: TtsVoice;
  isSelected: boolean;
  dense?: boolean;
}) {
  // Cheap hash → hue pair so each voice gets a stable, distinctive gradient
  // avatar without needing real assets.
  let hash = 0;
  for (let i = 0; i < voice.name.length; i += 1) hash = (hash * 31 + voice.name.charCodeAt(i)) | 0;
  const hueA = Math.abs(hash) % 360;
  const hueB = (hueA + 60) % 360;
  const initial = voice.name.charAt(0).toUpperCase();
  return (
    <div className="flex min-w-0 flex-1 items-center gap-2.5">
      <span
        aria-hidden
        className="flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white shadow-sm"
        style={{
          background: `linear-gradient(135deg, hsl(${hueA} 75% 55%), hsl(${hueB} 75% 45%))`,
        }}
      >
        {initial}
      </span>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-sm font-medium text-foreground">
          {voice.name}
          {voice.description ? (
            <span className="ml-1 font-normal text-muted-foreground">— {voice.description}</span>
          ) : null}
        </span>
        {!dense && (voice.gender || voice.accent) && (
          <span className="mt-0.5 flex items-center gap-1">
            {voice.gender && (
              <Badge variant="secondary" className="h-4 px-1.5 text-[10px] capitalize">
                {voice.gender}
              </Badge>
            )}
            {voice.accent && (
              <Badge variant="outline" className="h-4 px-1.5 text-[10px] capitalize">
                {voice.accent}
              </Badge>
            )}
          </span>
        )}
      </div>
      {isSelected && !dense && <span className="size-1.5 shrink-0 rounded-full bg-violet-500" />}
    </div>
  );
}

'use client';

import type { CallMetrics, PipelineConfigSnapshot, PipelineSpecSnapshot } from '@/types/callLog';
import { useMemo } from 'react';

// One row in a pipeline card (LLM / STT / TTS).
export interface PipelineStage {
  provider: string | null;
  model: string | null;
}

export interface CallConfigurationPipeline {
  llm: PipelineStage;
  stt: PipelineStage;
  tts: PipelineStage;
  language: string | null;
  voice: string | null;
}

interface UseCallConfigurationArgs {
  pipelineConfig: PipelineConfigSnapshot | null | undefined;
  metrics: CallMetrics | null | undefined;
}

interface UseCallConfigurationResult {
  data: CallConfigurationPipeline | null;
  loading: boolean;
}

// ─── pure helpers (no I/O, no React) ─────────────────────────────────────────

/** Matches a canonical UUID (v1–v5). Used to avoid surfacing raw ids as
 *  human-readable values when name resolution is unavailable. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isOpaqueId = (v: string | null | undefined): boolean => !!v && UUID_RE.test(v);

/** Returns the value only if it's a usable display string (not a UUID). */
function displayable(v: string | null | undefined): string | null {
  if (!v) return null;
  return isOpaqueId(v) ? null : v;
}

/** First non-empty `model` in a metrics array (LLM / STT / TTS usage rows). */
function firstModel<T extends { model: string | null }>(
  rows: T[] | null | undefined,
): string | null {
  if (!rows?.length) return null;
  return rows.find((r) => r.model)?.model ?? null;
}

/**
 * Resolve one pipeline stage from its call-time snapshot. Provider prefers the
 * resolved display name, falling back to the raw slug for older snapshots. Model
 * prefers the snapshot's resolved name, then the call's metrics, then a non-UUID
 * model id.
 */
function stageFrom(
  spec: PipelineSpecSnapshot | null | undefined,
  metricsModel: string | null,
): PipelineStage {
  return {
    provider: displayable(spec?.provider_display_name) ?? displayable(spec?.provider_name),
    model: displayable(spec?.model_name) ?? metricsModel ?? displayable(spec?.model_id),
  };
}

/**
 * Pure resolver. Turns the call's immutable pipeline snapshot (plus its runtime
 * metrics, used only as a model-name fallback) into a render-ready pipeline.
 * Kept separate from the hook so it stays trivially testable.
 */
export function resolvePipeline(
  snapshot: PipelineConfigSnapshot,
  metrics: CallMetrics | null | undefined,
): CallConfigurationPipeline {
  return {
    llm: stageFrom(snapshot.llm, firstModel(metrics?.llm_usage)),
    stt: stageFrom(snapshot.stt, firstModel(metrics?.stt_usage)),
    tts: stageFrom(snapshot.tts, firstModel(metrics?.tts_usage)),
    // Voice + language live on the TTS spec. Prefer the display forms captured at
    // call time (friendly voice name, display language), falling back to the raw
    // id / code for older snapshots, then null (renders an em-dash) — never the
    // live agent config.
    language: snapshot.tts?.language_display ?? snapshot.tts?.language ?? null,
    voice: displayable(snapshot.tts?.voice_name) ?? displayable(snapshot.tts?.voice_id),
  };
}

// ─── hook ────────────────────────────────────────────────────────────────────

/**
 * Derives the Call Configurations tab from the call's immutable
 * `pipeline_config` snapshot — the config that was actually used for THIS call.
 * No network I/O: everything needed was captured at call time, so editing the
 * agent afterwards can never rewrite a past call's displayed configuration.
 *
 * Returns `data: null` when the call has no snapshot (very old calls), which the
 * section renders as an "unavailable" empty state.
 */
export function useCallConfiguration({
  pipelineConfig,
  metrics,
}: UseCallConfigurationArgs): UseCallConfigurationResult {
  const data = useMemo<CallConfigurationPipeline | null>(
    () => (pipelineConfig ? resolvePipeline(pipelineConfig, metrics) : null),
    [pipelineConfig, metrics],
  );

  return { data, loading: false };
}

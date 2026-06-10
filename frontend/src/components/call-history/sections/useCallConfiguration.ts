'use client';

import { getAgent } from '@/services/agentsService';
import { listProviderCatalog } from '@/services/servicesService';
import { listTtsVoices } from '@/services/ttsService';
import type { AgentDetail } from '@/types/agent';
import type { CallMetrics } from '@/types/callLog';
import type { ProviderCatalogItem } from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { useEffect, useMemo, useState } from 'react';

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
  agentId: string | null | undefined;
  metrics: CallMetrics | null | undefined;
}

interface UseCallConfigurationResult {
  data: CallConfigurationPipeline | null;
  loading: boolean;
}

interface FetchedSources {
  agent: AgentDetail;
  catalog: ProviderCatalogItem[];
  voiceName: string | null;
}

// ─── session-scoped provider catalog cache ───────────────────────────────────
// The catalog rarely changes during a session, but the Pipeline tab can be
// opened many times across calls. A single in-flight promise dedupes
// concurrent loads and caches the result for the rest of the session.
let providerCatalogPromise: Promise<ProviderCatalogItem[]> | null = null;
function getProviderCatalog(): Promise<ProviderCatalogItem[]> {
  if (!providerCatalogPromise) {
    providerCatalogPromise = listProviderCatalog().catch((err) => {
      providerCatalogPromise = null; // allow retry on next mount
      throw err;
    });
  }
  return providerCatalogPromise;
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

/** First non-empty `model` in a metrics array (LLM / TTS usage rows). */
function firstModel<T extends { model: string | null }>(rows: T[] | undefined): string | null {
  if (!rows?.length) return null;
  return rows.find((r) => r.model)?.model ?? null;
}

/** Map a provider id → display name, falling back to the id itself. */
function providerName(
  catalog: ProviderCatalogItem[],
  providerId: string | null | undefined,
): string | null {
  if (!providerId) return null;
  return catalog.find((p) => p.id === providerId)?.display_name ?? providerId;
}

/**
 * Pure resolver. Joins fetched agent + catalog with the call's runtime
 * metrics to produce a render-ready pipeline. Kept separate from the
 * data-fetching hook so it stays trivially testable.
 */
function resolvePipeline(
  sources: FetchedSources,
  metrics: CallMetrics | null | undefined,
): CallConfigurationPipeline {
  const cfg = sources.agent.config ?? {};
  const llm = (cfg.llm_settings ?? {}) as Record<string, unknown>;
  const stt = (cfg.stt_settings ?? {}) as Record<string, unknown>;
  const voice = cfg.voice_settings ?? {};

  // Metrics carry the actual model name used during the call; prefer it over
  // the stored id which would otherwise show as a bare UUID. If neither is
  // human-readable, fall back to null so the UI renders an em-dash.
  const llmModel = firstModel(metrics?.llm_usage) ?? displayable(llm.model_id as string | null);
  const ttsModel = firstModel(metrics?.tts_usage) ?? displayable(voice.model_id as string | null);

  return {
    llm: {
      provider: providerName(sources.catalog, llm.provider_id as string | null),
      model: llmModel,
    },
    stt: {
      provider: providerName(sources.catalog, stt.provider_id as string | null),
      model: displayable(stt.model as string | null),
    },
    tts: {
      provider: providerName(sources.catalog, voice.provider_id),
      model: ttsModel,
    },
    language: voice.language ?? null,
    voice: sources.voiceName ?? displayable(voice.voice_id),
  };
}

// ─── hook ────────────────────────────────────────────────────────────────────

/**
 * Loads everything the Call Configurations tab needs:
 *   1. Agent detail — for the configured providers, models, voice, language
 *   2. Provider catalog — to resolve provider ids → display names
 *   3. TTS voices (conditional) — to resolve the configured voice id → name
 *
 * Fetches 1 + 2 in parallel; voice list runs only when provider + language
 * are present (avoids a redundant request on legacy/incomplete configs).
 *
 * Re-fetching keys off `agentId` only — metrics flow through the pure
 * `resolvePipeline` derive step, so a new metrics reference re-derives but
 * never re-hits the network.
 */
export function useCallConfiguration({
  agentId,
  metrics,
}: UseCallConfigurationArgs): UseCallConfigurationResult {
  const [sources, setSources] = useState<FetchedSources | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!agentId) {
      setSources(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const [agent, catalog] = await Promise.all([getAgent(agentId), getProviderCatalog()]);
        if (cancelled) return;

        const voice = agent.config?.voice_settings ?? {};
        let voiceName: string | null = null;
        if (voice.provider_id && voice.language && voice.voice_id) {
          try {
            const voices = await listTtsVoices(
              voice.provider_id,
              voice.language,
              (voice.model_id as string | null | undefined) ?? null,
            );
            if (!cancelled) {
              voiceName = voices.find((v) => v.id === voice.voice_id)?.name ?? null;
            }
          } catch {
            // Non-fatal — fall back to showing the voice id in the resolver.
          }
        }
        if (cancelled) return;

        setSources({ agent, catalog, voiceName });
      } catch (err) {
        if (!cancelled) handleApiError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [agentId]);

  const data = useMemo<CallConfigurationPipeline | null>(
    () => (sources ? resolvePipeline(sources, metrics) : null),
    [sources, metrics],
  );

  return { data, loading };
}

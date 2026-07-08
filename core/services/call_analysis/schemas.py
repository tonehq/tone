"""Pydantic models describing the call-analysis report (schema_version 1.0)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Word(BaseModel):
    word: str
    start: float
    end: float
    confidence: float = 0.0
    speaker: Optional[int] = None
    punctuated_word: Optional[str] = None


class Utterance(BaseModel):
    speaker: Optional[int] = None
    role: Optional[str] = None  # "agent" | "customer" | "unknown" | None
    start: float
    end: float
    text: str
    confidence: float = 0.0
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None


class STTSection(BaseModel):
    provider: str = "deepgram"
    model: str
    duration_seconds: float
    language: Optional[str] = None
    full_transcript: str
    utterances: List[Utterance] = []
    topics: List[str] = []
    intents: List[str] = []
    deepgram_summary: Optional[str] = None


class SpeakerMetrics(BaseModel):
    speaker: int
    role: Optional[str] = None
    talk_time_seconds: float
    talk_time_pct: float
    words: int
    wpm: float
    filler_word_count: int
    filler_words: Dict[str, int] = {}
    longest_monologue_seconds: float
    interruptions_initiated: int
    avg_response_latency_seconds: Optional[float] = None


class DeadAirEvent(BaseModel):
    start: float
    end: float
    duration: float


class MetricsSection(BaseModel):
    total_duration_seconds: float
    speakers: List[SpeakerMetrics] = []
    silence_total_seconds: float
    silence_pct: float
    dead_air_events: List[DeadAirEvent] = []
    overlap_total_seconds: float
    interruption_count: int
    turn_count: int


class Discrepancy(BaseModel):
    kind: str  # "missing_in_live" | "extra_in_live" | "mismatch"
    live_text: Optional[str] = None
    stt_text: Optional[str] = None
    similarity: float = 0.0
    approx_time: Optional[float] = None


class CrossCheckSection(BaseModel):
    live_transcript_available: bool
    wer: Optional[float] = None
    turn_alignment_rate: Optional[float] = None
    discrepancies: List[Discrepancy] = []


class SentimentPoint(BaseModel):
    time: float
    speaker_role: Optional[str] = None
    sentiment: str
    score: float


class LLMSection(BaseModel):
    provider: str = ""
    model: str = ""
    summary: str
    call_outcome: str
    sentiment_arc: str
    agent_quality_score: int = Field(ge=0, le=10)
    agent_quality_rationale: str
    action_items: List[str] = []
    compliance_flags: List[str] = []


class AnalysisReport(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime
    source: Dict[str, Any] = {}
    call_info: Optional[Dict[str, Any]] = None
    stt: Optional[STTSection] = None
    metrics: Optional[MetricsSection] = None
    sentiment_timeline: List[SentimentPoint] = []
    crosscheck: Optional[CrossCheckSection] = None
    llm_analysis: Optional[LLMSection] = None
    skipped_layers: List[str] = []
    warnings: List[str] = []

"""Call-quality metrics derived purely from STT utterance/word timings."""

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from core.services.call_analysis.schemas import (
    DeadAirEvent,
    MetricsSection,
    SentimentPoint,
    SpeakerMetrics,
    Utterance,
)
from core.services.call_analysis.stt_engine import STTResult

FILLER_WORDS = {"uh", "um", "mhmm", "mm-hmm", "uh-huh", "hmm", "er", "ah", "erm"}

_MONOLOGUE_MERGE_GAP = 1.0  # merge same-speaker utterances closer than this


def compute_metrics(
    stt: STTResult,
    role_map: Optional[Dict[int, str]] = None,
    dead_air_threshold: float = 3.0,
    interruption_overlap: float = 0.5,
) -> MetricsSection:
    role_map = role_map or {}
    utterances = sorted(stt.utterances, key=lambda u: (u.start, u.end))
    total_duration = stt.duration or (max((u.end for u in utterances), default=0.0))

    by_speaker: Dict[int, List[Utterance]] = defaultdict(list)
    for u in utterances:
        by_speaker[u.speaker if u.speaker is not None else -1].append(u)

    interruptions = _count_interruptions(utterances, interruption_overlap)
    latencies = _response_latencies(utterances)
    filler_counts = _filler_counts_by_speaker(stt)

    speakers: List[SpeakerMetrics] = []
    for speaker_id, utts in sorted(by_speaker.items()):
        talk_time = sum(u.end - u.start for u in utts)
        word_count = sum(len(u.text.split()) for u in utts)
        fillers = filler_counts.get(speaker_id, Counter())
        speakers.append(
            SpeakerMetrics(
                speaker=speaker_id,
                role=role_map.get(speaker_id),
                talk_time_seconds=round(talk_time, 2),
                talk_time_pct=round(100 * talk_time / total_duration, 1) if total_duration else 0.0,
                words=word_count,
                wpm=round(word_count / (talk_time / 60), 1) if talk_time else 0.0,
                filler_word_count=sum(fillers.values()),
                filler_words=dict(fillers),
                longest_monologue_seconds=round(_longest_monologue(utts), 2),
                interruptions_initiated=interruptions.get(speaker_id, 0),
                avg_response_latency_seconds=(
                    round(sum(latencies[speaker_id]) / len(latencies[speaker_id]), 2)
                    if latencies.get(speaker_id)
                    else None
                ),
            )
        )

    silence_total, dead_air = _silence_and_dead_air(utterances, total_duration, dead_air_threshold)
    overlap_total = _total_overlap(utterances)

    return MetricsSection(
        total_duration_seconds=round(total_duration, 2),
        speakers=speakers,
        silence_total_seconds=round(silence_total, 2),
        silence_pct=round(100 * silence_total / total_duration, 1) if total_duration else 0.0,
        dead_air_events=dead_air,
        overlap_total_seconds=round(overlap_total, 2),
        interruption_count=sum(interruptions.values()),
        turn_count=_turn_count(utterances),
    )


def build_sentiment_timeline(
    stt: STTResult, role_map: Optional[Dict[int, str]] = None
) -> List[SentimentPoint]:
    role_map = role_map or {}
    return [
        SentimentPoint(
            time=round(u.start, 2),
            speaker_role=role_map.get(u.speaker) if u.speaker is not None else None,
            sentiment=u.sentiment,
            score=round(u.sentiment_score or 0.0, 3),
        )
        for u in stt.utterances
        if u.sentiment
    ]


def _merged_intervals(utterances: List[Utterance]) -> List[Tuple[float, float]]:
    merged: List[Tuple[float, float]] = []
    for u in sorted(utterances, key=lambda x: x.start):
        if merged and u.start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], u.end))
        else:
            merged.append((u.start, u.end))
    return merged


def _silence_and_dead_air(
    utterances: List[Utterance], total_duration: float, threshold: float
) -> Tuple[float, List[DeadAirEvent]]:
    if not utterances:
        return total_duration, []
    merged = _merged_intervals(utterances)
    speech = sum(end - start for start, end in merged)
    silence = max(0.0, total_duration - speech)

    dead_air: List[DeadAirEvent] = []
    gaps = [(0.0, merged[0][0])]
    gaps += [(merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]
    if total_duration > merged[-1][1]:
        gaps.append((merged[-1][1], total_duration))
    for start, end in gaps:
        if end - start > threshold:
            dead_air.append(
                DeadAirEvent(start=round(start, 2), end=round(end, 2), duration=round(end - start, 2))
            )
    return silence, dead_air


def _count_interruptions(utterances: List[Utterance], min_overlap: float) -> Dict[int, int]:
    """Speaker B interrupts when their utterance starts before A's ends by > min_overlap."""
    counts: Dict[int, int] = defaultdict(int)
    for i, current in enumerate(utterances):
        for previous in utterances[max(0, i - 3) : i]:
            if previous.speaker == current.speaker or current.speaker is None:
                continue
            if previous.end - current.start > min_overlap:
                counts[current.speaker] += 1
                break
    return counts


def _total_overlap(utterances: List[Utterance]) -> float:
    total = 0.0
    for i, current in enumerate(utterances):
        for previous in utterances[max(0, i - 3) : i]:
            if previous.speaker == current.speaker:
                continue
            total += max(0.0, min(previous.end, current.end) - current.start)
    return total


def _longest_monologue(utterances: List[Utterance]) -> float:
    """Max span of consecutive utterances (same speaker list) with gaps < merge threshold."""
    longest = 0.0
    span_start: Optional[float] = None
    span_end: Optional[float] = None
    for u in sorted(utterances, key=lambda x: x.start):
        if span_end is not None and u.start - span_end < _MONOLOGUE_MERGE_GAP:
            span_end = max(span_end, u.end)
        else:
            if span_start is not None:
                longest = max(longest, span_end - span_start)
            span_start, span_end = u.start, u.end
    if span_start is not None:
        longest = max(longest, span_end - span_start)
    return longest


def _response_latencies(utterances: List[Utterance]) -> Dict[int, List[float]]:
    """Gap between the previous speaker's utterance end and this speaker's start,
    collected per responding speaker at each turn change."""
    latencies: Dict[int, List[float]] = defaultdict(list)
    for prev, curr in zip(utterances, utterances[1:]):
        if curr.speaker is None or prev.speaker == curr.speaker:
            continue
        gap = curr.start - prev.end
        if 0 <= gap < 30:  # ignore overlaps and pathological gaps
            latencies[curr.speaker].append(gap)
    return latencies


def _turn_count(utterances: List[Utterance]) -> int:
    turns = 0
    last_speaker: Optional[int] = None
    for u in utterances:
        if u.speaker != last_speaker:
            turns += 1
            last_speaker = u.speaker
    return turns


def _filler_counts_by_speaker(stt: STTResult) -> Dict[int, Counter]:
    counts: Dict[int, Counter] = defaultdict(Counter)
    if stt.words:
        for w in stt.words:
            token = w.word.lower().strip(".,!?")
            if token in FILLER_WORDS:
                counts[w.speaker if w.speaker is not None else -1][token] += 1
    else:  # fall back to utterance text
        for u in stt.utterances:
            for token in u.text.lower().split():
                token = token.strip(".,!?")
                if token in FILLER_WORDS:
                    counts[u.speaker if u.speaker is not None else -1][token] += 1
    return counts

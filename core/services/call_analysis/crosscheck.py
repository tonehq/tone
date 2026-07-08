"""Cross-check the live in-call transcript against the batch STT output.

Uses stdlib difflib for alignment and an approximate WER — good enough to flag
live-transcription drift without adding a jiwer dependency.
"""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from core.services.call_analysis.schemas import CrossCheckSection, Discrepancy
from core.services.call_analysis.stt_engine import STTResult

_MATCH_THRESHOLD = 0.6
_MISMATCH_THRESHOLD = 0.45  # below this, a live entry counts as unmatched, not mis-transcribed
_MIN_STT_WORDS_FOR_MISSING = 4

_ROLE_LABELS = {"assistant": "agent", "user": "customer"}


_DIGIT_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def _normalize_tokens(text: str) -> List[str]:
    tokens = re.sub(r"[^a-z0-9\s']", " ", text.lower()).split()
    # Expand digit runs to spoken words ("45678" -> "four five ...") so
    # smart-formatted STT output aligns with verbatim live transcripts.
    normalized: List[str] = []
    for token in tokens:
        if token.isdigit():
            normalized.extend(_DIGIT_WORDS[int(d)] for d in token)
        else:
            normalized.append(token)
    return normalized


def map_speakers_to_roles(
    stt: STTResult, live: Optional[List[dict]]
) -> Dict[int, str]:
    """Majority-vote each diarized speaker onto agent/customer by best text match
    against the live transcript entries. Unmapped speakers become "unknown"."""
    speakers = {u.speaker for u in stt.utterances if u.speaker is not None}
    if not speakers:
        return {}
    if not live:
        return {}

    votes: Dict[int, Counter] = {s: Counter() for s in speakers}
    for utt in stt.utterances:
        if utt.speaker is None:
            continue
        best_role, best_score = None, 0.0
        utt_tokens = " ".join(_normalize_tokens(utt.text))
        for entry in live:
            score = SequenceMatcher(
                None, utt_tokens, " ".join(_normalize_tokens(entry["text"]))
            ).ratio()
            if score > best_score:
                best_score, best_role = score, _ROLE_LABELS.get(entry["role"])
        if best_role and best_score >= 0.3:
            votes[utt.speaker][best_role] += 1

    role_map: Dict[int, str] = {}
    for speaker, counter in votes.items():
        role_map[speaker] = counter.most_common(1)[0][0] if counter else "unknown"
    return role_map


def cross_check(stt: STTResult, live: Optional[List[dict]]) -> CrossCheckSection:
    if not live:
        return CrossCheckSection(live_transcript_available=False)

    ref_tokens = [t for u in stt.utterances for t in _normalize_tokens(u.text)]
    hyp_tokens = [t for e in live for t in _normalize_tokens(e["text"])]
    wer = _approximate_wer(ref_tokens, hyp_tokens) if ref_tokens else None

    discrepancies: List[Discrepancy] = []
    matched_utterances = set()
    matched_live = 0
    for entry in live:
        entry_norm = " ".join(_normalize_tokens(entry["text"]))
        best_i, best_score = None, 0.0
        for i, utt in enumerate(stt.utterances):
            score = SequenceMatcher(
                None, entry_norm, " ".join(_normalize_tokens(utt.text))
            ).ratio()
            if score > best_score:
                best_score, best_i = score, i
        if best_i is not None and best_score >= _MATCH_THRESHOLD:
            matched_utterances.add(best_i)
            matched_live += 1
        elif best_i is not None and best_score >= _MISMATCH_THRESHOLD:
            matched_utterances.add(best_i)
            discrepancies.append(
                Discrepancy(
                    kind="mismatch",
                    live_text=entry["text"],
                    stt_text=stt.utterances[best_i].text,
                    similarity=round(best_score, 3),
                    approx_time=stt.utterances[best_i].start,
                )
            )
        else:
            discrepancies.append(
                Discrepancy(
                    kind="extra_in_live",
                    live_text=entry["text"],
                    similarity=round(best_score, 3),
                )
            )

    for i, utt in enumerate(stt.utterances):
        if i in matched_utterances:
            continue
        if len(_normalize_tokens(utt.text)) >= _MIN_STT_WORDS_FOR_MISSING:
            discrepancies.append(
                Discrepancy(
                    kind="missing_in_live",
                    stt_text=utt.text,
                    approx_time=utt.start,
                )
            )

    return CrossCheckSection(
        live_transcript_available=True,
        wer=round(wer, 3) if wer is not None else None,
        turn_alignment_rate=round(matched_live / len(live), 3) if live else None,
        discrepancies=discrepancies,
    )


def _approximate_wer(reference: List[str], hypothesis: List[str]) -> float:
    """WER ≈ (S + D + I) / N derived from SequenceMatcher opcodes (STT = reference)."""
    if not reference:
        return 0.0
    substitutions = deletions = insertions = 0
    matcher = SequenceMatcher(None, reference, hypothesis, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        ref_span, hyp_span = i2 - i1, j2 - j1
        if op == "replace":
            substitutions += min(ref_span, hyp_span)
            deletions += max(0, ref_span - hyp_span)
            insertions += max(0, hyp_span - ref_span)
        elif op == "delete":
            deletions += ref_span
        elif op == "insert":
            insertions += hyp_span
    return (substitutions + deletions + insertions) / len(reference)

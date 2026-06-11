import type { CallLogRow } from '@/types/callLog';

/**
 * Pick the duration value that matches what a user would observe.
 *
 * `recording_duration_seconds` is the encoded MP3 length — what the audio
 * player plays — and is the truthful "how long was this call". It only
 * exists for calls that produced a recording. For everything else we fall
 * back to `duration_seconds`, which is the wall-clock from call-log
 * creation to completion (includes pipeline setup, client handshake, R2
 * upload, DB writes — so it can be a few seconds longer than the audio).
 */
export function getDisplayDurationSeconds(
  call: Pick<CallLogRow, 'duration_seconds' | 'recording_duration_seconds'>,
): number | null {
  if (call.recording_duration_seconds != null) return call.recording_duration_seconds;
  return call.duration_seconds;
}

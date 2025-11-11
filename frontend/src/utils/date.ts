import dayjs, { Dayjs } from 'dayjs';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
dayjs.extend(timezone);

export type DateInput = string | number | Date | Dayjs | null | undefined;

export const toDayjs = (input: DateInput): Dayjs | null => {
  if (input === null || input === undefined) return null;
  const value = dayjs(input);
  return value.isValid() ? value : null;
};

export const formatDate = (
  input: DateInput,
  format: string = 'MMMM D, YYYY',
  tz?: string,
): string => {
  const d = toDayjs(input);
  if (!d) return 'Unknown';
  const source = tz ? d.tz(tz) : d;
  return source.format(format);
};

export const formatEpochSeconds = (
  epochSeconds: number | null | undefined,
  format: string = 'MMMM D, YYYY',
  tz?: string,
): string => {
  if (!epochSeconds && epochSeconds !== 0) return 'Unknown';
  const millis = epochSeconds * 1000;
  return formatDate(millis, format, tz);
};

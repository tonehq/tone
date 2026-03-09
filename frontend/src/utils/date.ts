import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);

export const DATE_FORMAT = 'DD MMM YYYY, HH:mm A';

export function formatDate(value: number | string, format: string = DATE_FORMAT): string {
  if (typeof value === 'number') {
    return dayjs.unix(value).format(format);
  }
  return dayjs.utc(value).local().format(format);
}

export function formatNow(format: string = DATE_FORMAT): string {
  return dayjs().format(format);
}

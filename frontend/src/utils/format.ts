import { isString, startCase, toLower, trim } from 'lodash';

import { formatEpochSeconds } from '@/utils/date';

export const formatDisplayName = (
  firstName?: string | null,
  lastName?: string | null,
  fallback?: string,
): string => {
  const safeFirst = isString(firstName) ? trim(firstName) : '';
  const safeLast = isString(lastName) ? trim(lastName) : '';
  const joined = [safeFirst, safeLast].filter(Boolean).join(' ').trim();
  if (!joined) {
    return fallback ? fallback : '';
  }
  return startCase(toLower(joined));
};

export const formatEmailOrUsername = (
  email?: string | null,
  username?: string | null,
  fallback = '',
): string => {
  const value = (email || username || fallback).toString();
  return value;
};

export const capitalizeLabel = (value: string): string => {
  if (!value) return '';
  return startCase(toLower(value));
};

export const getInitialsFromName = (name: string): string => {
  if (!name) return '';
  if (name.includes('@')) {
    return name.charAt(0).toUpperCase();
  }
  return name
    .split(' ')
    .filter(Boolean)
    .map((n) => n[0])
    .join('')
    .toUpperCase();
};

export const formatEpochToDate = (
  epochSeconds?: number | null,
  _locale: string = 'en-US',
): string => {
  if (epochSeconds === null || epochSeconds === undefined) return 'Unknown';
  return formatEpochSeconds(epochSeconds);
};

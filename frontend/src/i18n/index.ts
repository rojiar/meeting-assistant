export { t } from './messages';

export function formatDate(iso: string, _locale?: string): string {
  try {
    return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export function priorityLabel(p: string, _locale?: string): string {
  const map = t.priority as Record<string, string>;
  return map[p] ?? p;
}

export function meetingTypeLabel(type: string, _locale?: string): string {
  const map = t.meetingTypes as Record<string, string>;
  return map[type] ?? type;
}

export function serverError(_locale?: string): string {
  return t.common.serverError;
}

export function transcribeError(_locale?: string): string {
  return t.common.transcribeError;
}

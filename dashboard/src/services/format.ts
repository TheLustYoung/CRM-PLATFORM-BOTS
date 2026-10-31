export const bytes = (n: number | null | undefined) => {
  if (n == null) return '—';
  if (n < 1e3) return `${n} B`;
  if (n < 1e6) return `${(n / 1e3).toFixed(1)} KB`;
  if (n < 1e9) return `${(n / 1e6).toFixed(1)} MB`;
  return `${(n / 1e9).toFixed(2)} GB`;
};

export const dateTime = (value: string | null | undefined, lang: string) =>
  value ? new Date(value.endsWith('Z') || value.includes('+') ? value : value + 'Z').toLocaleString(lang) : '—';

export const number = (value: number | null | undefined, lang: string) =>
  value == null ? '—' : Number(value).toLocaleString(lang);

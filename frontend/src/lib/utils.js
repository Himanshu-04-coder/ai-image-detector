// Tiny classname combiner — avoids pulling in clsx just for one feature.
export function cn(...args) {
  return args.flat().filter(Boolean).join(' ');
}

// Format a confidence value (0..1 or 0..100) as a percentage string.
export function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const n = Number(value);
  // Heuristic: anything <= 1 is treated as a fraction, otherwise percent.
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
}

// Normalize a verdict string to one of the canonical labels we render.
export function normalizeVerdict(v) {
  if (!v) return 'UNKNOWN';
  const s = String(v).toUpperCase();
  if (s.includes('AI') || s.includes('FAKE') || s.includes('GENERATED')) return 'AI-GENERATED';
  if (s.includes('REAL') || s.includes('AUTHENTIC')) return 'REAL';
  return s;
}

export function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

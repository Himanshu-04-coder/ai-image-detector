import { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, History, RefreshCw, ImageOff } from 'lucide-react';

import PageHeader from '../components/PageHeader';
import Spinner from '../components/Spinner';
import VerdictBadge from '../components/VerdictBadge';
import EmptyState from '../components/EmptyState';
import { getHistory, normalizeError } from '../api/client';
import notify from '../lib/toast';
import { cn, formatDate, normalizeVerdict } from '../lib/utils';

const COLUMNS = [
  { key: 'thumbnail',  label: 'Image',      sortable: false },
  { key: 'verdict',    label: 'Verdict',    sortable: true },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'filename',   label: 'Filename',   sortable: true },
  { key: 'timestamp',  label: 'When',       sortable: true },
];

function getSortValue(row, key) {
  switch (key) {
    case 'verdict':
      return normalizeVerdict(row.verdict ?? row.label);
    case 'confidence':
      return Number(row.confidence ?? row.score ?? 0);
    case 'filename':
      return String(row.filename ?? row.name ?? '');
    case 'timestamp':
      return new Date(row.timestamp ?? row.created_at ?? row.time ?? 0).getTime();
    default:
      return null;
  }
}

function resolveThumbUrl(thumb) {
  if (!thumb) return null;
  if (typeof thumb === 'string') {
    if (thumb.startsWith('data:') || thumb.startsWith('http') || thumb.startsWith('blob:')) {
      return thumb;
    }
    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    return `${base.replace(/\/$/, '')}/${thumb.replace(/^\//, '')}`;
  }
  if (thumb.url) return resolveThumbUrl(thumb.url);
  if (thumb.b64) return `data:image/png;base64,${thumb.b64}`;
  return null;
}

export default function HistoryPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortKey, setSortKey] = useState('timestamp');
  const [sortDir, setSortDir] = useState('desc');

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getHistory();
      const arr = Array.isArray(data) ? data : data.history ?? data.items ?? [];
      setRows(arr);
    } catch (e) {
      const norm = normalizeError(e);
      setError(norm.friendlyMessage);
      notify.error(norm.friendlyMessage);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const va = getSortValue(a, sortKey);
      const vb = getSortValue(b, sortKey);
      if (va === vb) return 0;
      const cmp = va > vb ? 1 : -1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'timestamp' || key === 'confidence' ? 'desc' : 'asc');
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prediction history"
        subtitle="Every image you've analyzed through the backend."
        icon={History}
        actions={
          <button onClick={load} className="btn-ghost" disabled={loading}>
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            Refresh
          </button>
        }
      />

      <div className="rotate-[-1]">
        <div className="card overflow-hidden relative">
          <div className="absolute -top-2 -right-2 w-4 h-4 bg-marker rounded-full shadow-hard z-10" />
          {loading ? (
            <div className="p-6"><Spinner label="Loading history…" /></div>
          ) : error ? (
            <div className="p-6 text-sm border-marker bg-marker/10 text-marker wobbly-3">
              {error}
            </div>
          ) : sorted.length === 0 ? (
            <EmptyState
              className="py-12"
              icon={ImageOff}
              title="No predictions yet"
              description={"Once you analyse an image it will show up here. " +
                           "Head to the Analyze page to run your first scan."}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    {COLUMNS.map((col) => {
                      const active = sortKey === col.key;
                      return (
                        <th
                          key={col.key}
                          className={cn(
                            col.sortable && 'cursor-pointer select-none hover:text-pencil'
                          )}
                          onClick={() => col.sortable && toggleSort(col.key)}
                        >
                          <span className="inline-flex items-center gap-1.5">
                            {col.label}
                            {col.sortable && (
                              active
                                ? (sortDir === 'asc'
                                    ? <ArrowUp className="w-3 h-3" />
                                    : <ArrowDown className="w-3 h-3" />)
                                : <ArrowUpDown className="w-3 h-3 opacity-40" />
                          )}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, i) => {
                  const thumb = resolveThumbUrl(row.thumbnail_path ?? row.thumbnail ?? row.thumb);
                  const verdict = row.label ?? row.verdict;
                  const confidence = row.confidence ?? row.score;
                  return (
                    <tr key={row.id ?? i}>
                      <td>
                        <div className="w-10 h-10 wobbly-2 overflow-hidden
                                        border-2 border-pencil
                                        bg-paper">
                          {thumb ? (
                            <img src={thumb} alt=""
                                 className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full grid place-items-center
                                            text-pencil/40">
                              <ImageOff className="w-4 h-4" />
                            </div>
                          )}
                        </div>
                      </td>
                      <td>
                        <VerdictBadge
                          verdict={verdict}
                          confidence={confidence}
                          size="sm"
                        />
                      </td>
                      <td className="font-medium tabular-nums">
                        {confidence !== undefined && confidence !== null
                          ? `${(Number(confidence) <= 1
                                ? Number(confidence) * 100
                                : Number(confidence)).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="text-pencil/60
                                     max-w-[16rem] truncate">
                        {row.filename ?? row.name ?? '—'}
                      </td>
                      <td className="text-pencil/60">
                        {formatDate(row.timestamp ?? row.created_at ?? row.time)}
                      </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

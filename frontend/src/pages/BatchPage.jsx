import { useState } from 'react';
import { Files, RotateCcw, Trash2, AlertTriangle } from 'lucide-react';

import PageHeader from '../components/PageHeader';
import DropZone from '../components/DropZone';
import Spinner from '../components/Spinner';
import VerdictBadge from '../components/VerdictBadge';
import EmptyState from '../components/EmptyState';
import { predictBatch, normalizeError } from '../api/client';
import notify from '../lib/toast';
import { validateImageFile } from '../lib/validation';

export default function BatchPage() {
  const [files, setFiles] = useState([]); // File[]
  const [previews, setPreviews] = useState({}); // filename -> objectURL
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function handleFiles(newFiles) {
    setError(null);
    setResults(null);
    const merged = [...files];
    const previewsCopy = { ...previews };
    newFiles.forEach((f) => {
      // DropZone already validates, but guard here too.
      if (validateImageFile(f)) return;
      const exists = merged.some(
        (m) => m.name === f.name && m.size === f.size && m.lastModified === f.lastModified
      );
      if (!exists) {
        merged.push(f);
        previewsCopy[f.name] = URL.createObjectURL(f);
      }
    });
    setFiles(merged);
    setPreviews(previewsCopy);
  }

  function removeFile(name) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
    setPreviews((prev) => {
      if (prev[name]) URL.revokeObjectURL(prev[name]);
      const copy = { ...prev };
      delete copy[name];
      return copy;
    });
  }

  function reset() {
    Object.values(previews).forEach(URL.revokeObjectURL);
    setFiles([]);
    setPreviews({});
    setResults(null);
    setError(null);
  }

  async function runBatch() {
    if (files.length === 0) return;
    const tId = notify.loading(`Analysing ${files.length} image(s)…`);
    setLoading(true);
    setError(null);
    try {
      const data = await predictBatch(files);
      // Backend returns a bare List[PredictResponse]. Each entry is either
      // {label, confidence, heatmap_url} or {error, filename} if the item
      // failed validation server-side.
      const arr = Array.isArray(data) ? data : data.results ?? [];
      setResults(arr);
      notify.dismiss(tId);
      const failed = arr.filter((r) => r?.error).length;
      if (failed > 0) {
        notify.warning(`Completed with ${failed} failure(s).`);
      } else {
        notify.success(`Analysed ${arr.length} image(s).`);
      }
    } catch (e) {
      const norm = normalizeError(e);
      setError(norm.friendlyMessage);
      notify.dismiss(tId);
      notify.error(norm.friendlyMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Batch analysis"
        subtitle="Upload multiple images and get verdicts in a single request."
        icon={Files}
        actions={files.length > 0 && !loading ? (
          <button onClick={reset} className="btn-ghost">
            <RotateCcw className="w-4 h-4" /> Reset
          </button>
        ) : null}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: drop + queue */}
        <div className="lg:col-span-2 space-y-4">
          <DropZone multiple onFiles={handleFiles} />

          {files.length > 0 && (
            <div className="rotate-1">
              <div className="card p-4 relative">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-20 h-6 bg-white/40 backdrop-blur-sm border border-pencil/20 rotate-[-2deg] z-10" />
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-semibold font-heading text-lg">
                    Queued ({files.length})
                  </div>
                  <button
                    onClick={runBatch}
                    disabled={loading}
                    className="btn-primary text-xs px-3 py-1.5"
                  >
                    {loading ? 'Analyzing…' : 'Analyze all'}
                  </button>
                </div>
                <ul className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {files.map((f) => (
                    <li key={`${f.name}-${f.lastModified}`}
                        className="relative group wobbly-3 overflow-hidden
                                   border-2 border-pencil
                                   bg-paper">
                      <div className="aspect-square">
                        <img src={previews[f.name]} alt=""
                             className="w-full h-full object-cover" />
                      </div>
                      <div className="px-2 py-1.5 text-xs truncate text-pencil">
                        {f.name}
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(f.name)}
                        className="absolute top-1.5 right-1.5 p-1 rounded-md
                                  bg-pencil text-white opacity-0
                                  group-hover:opacity-100 transition"
                        aria-label={`Remove ${f.name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {loading && (
            <div className="card-padded">
              <Spinner label={`Running batch on ${files.length} image(s)…`} />
            </div>
          )}

          {error && !loading && (
            <div className="card-padded border-marker bg-marker/10 text-marker text-sm wobbly-3">
              {error}
            </div>
          )}
        </div>

        {/* Right: results table */}
        <div className="lg:col-span-1 rotate-[-1]">
          <div className="card overflow-hidden relative">
            <div className="absolute -top-2 -right-2 w-4 h-4 bg-marker rounded-full shadow-hard z-10" />
            <div className="px-4 py-3 border-b-2 border-pencil">
              <div className="text-sm font-semibold font-heading text-lg">Results</div>
              <div className="text-xs text-pencil/60">
                {results
                  ? `${results.length} analysed`
                  : files.length > 0
                    ? 'Click "Analyze all" to start'
                    : 'No results yet'}
              </div>
            </div>

            {!results ? (
              <EmptyState
                className="py-10"
                icon={Files}
                title="No batch results yet"
                description="Drop some images on the left and click Analyze all."
              />
            ) : results.length === 0 ? (
              <EmptyState
                className="py-10"
                icon={AlertTriangle}
                title="Backend returned an empty batch"
                description="Something went wrong on the server side. Check FastAPI logs."
              />
            ) : (
              <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
                <table className="table-base">
                  <thead>
                    <tr>
                      <th>Image</th>
                      <th>Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => {
                      const filename = r.filename ?? files[i]?.name ?? `image-${i}`;
                      // For the thumbnail, fall back to the queued preview.
                      const thumb = previews[filename] ?? null;

                      // Per-file server-side error (e.g. invalid image).
                      if (r.error) {
                        return (
                          <tr key={i}>
                            <td>
                              <div className="flex items-center gap-3 min-w-0">
                                <div className="w-10 h-10 rounded-md overflow-hidden
                                                border border-red-200 dark:border-red-800
                                                bg-red-50 dark:bg-red-900/20 shrink-0">
                                  {thumb ? (
                                    <img src={thumb} alt=""
                                        className="w-full h-full object-cover opacity-50" />
                                  ) : (
                                    <AlertTriangle className="w-5 h-5 m-auto mt-2 text-red-500" />
                                  )}
                                </div>
                                <div className="min-w-0">
                                  <div className="text-xs font-medium truncate max-w-[10rem]">
                                    {filename}
                                  </div>
                                  <div className="text-xs text-red-600 dark:text-red-400 truncate max-w-[10rem]">
                                    {r.error}
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td>
                              <span className="text-xs px-2 py-1 rounded-full
                                              bg-red-50 text-red-700 ring-1 ring-red-200
                                              dark:bg-red-900/30 dark:text-red-300
                                              dark:ring-red-800">
                                Failed
                              </span>
                            </td>
                          </tr>
                        );
                      }

                      return (
                        <tr key={i}>
                          <td>
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-10 h-10 rounded-md overflow-hidden
                                              border border-surface-200
                                              dark:border-surface-700
                                              bg-surface-100 dark:bg-surface-800 shrink-0">
                                {thumb && (
                                  <img src={thumb} alt=""
                                      className="w-full h-full object-cover" />
                                )}
                              </div>
                              <div className="min-w-0">
                                <div className="text-xs font-medium truncate
                                                max-w-[10rem]">
                                  {filename}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td>
                            <VerdictBadge
                              verdict={r.label}
                              confidence={r.confidence}
                              size="sm"
                            />
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
    </div>
  );
}

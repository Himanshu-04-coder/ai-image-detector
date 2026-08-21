import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Upload, Sparkles, Eye, EyeOff, RotateCcw } from 'lucide-react';

import PageHeader from '../components/PageHeader';
import DropZone from '../components/DropZone';
import Spinner from '../components/Spinner';
import VerdictBadge from '../components/VerdictBadge';
import Accordion from '../components/Accordion';
import EmptyState from '../components/EmptyState';
import { predictDetailed, normalizeError } from '../api/client';
import { cn, formatPct } from '../lib/utils';
import notify from '../lib/toast';
import { validateImageFile } from '../lib/validation';

/** Convert backend heatmap/spectrum (data URL OR object URL OR relative path) to a src. */
function resolveAssetUrl(asset) {
  if (!asset) return null;
  if (typeof asset === 'string') {
    if (asset.startsWith('data:') || asset.startsWith('http') || asset.startsWith('blob:')) {
      return asset;
    }
    const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    return `${base.replace(/\/$/, '')}/${asset.replace(/^\//, '')}`;
  }
  if (asset.url) return resolveAssetUrl(asset.url);
  if (asset.b64) return `data:image/png;base64,${asset.b64}`;
  return null;
}

/**
 * Map the discrete EXIF risk score to a 0..1 value for the progress bar.
 * "Low"    -> 0.20
 * "Medium" -> 0.55
 * "High"   -> 0.85
 * Anything else falls back to 0.20.
 */
function exifRiskToNumber(risk) {
  if (risk === 'High') return 0.85;
  if (risk === 'Medium') return 0.55;
  return 0.20;
}

function ExifPanel({ exif }) {
  if (!exif) {
    return (
      <div className="text-sm text-surface-500 dark:text-surface-400">
        No EXIF data returned by the backend.
      </div>
    );
  }

  const risk = exif.risk_score ?? 'Low';
  const reasons = exif.risk_reasons ?? [];
  const score = exifRiskToNumber(risk);
  const isHigh = risk === 'High' || risk === 'Medium';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-surface-500
                          dark:text-surface-400">
            EXIF risk score
          </div>
          <div className="mt-1 text-2xl font-semibold">{risk}</div>
          {exif.camera_make || exif.camera_model ? (
            <div className="text-xs text-surface-500 dark:text-surface-400 mt-1">
              {[exif.camera_make, exif.camera_model].filter(Boolean).join(' ')}
            </div>
          ) : null}
          {exif.software ? (
            <div className="text-xs text-surface-500 dark:text-surface-400">
              Software: {exif.software}
            </div>
          ) : null}
        </div>
        <span
          className={cn(
            'text-xs px-2 py-1 rounded-full ring-1',
            isHigh
              ? 'bg-red-50 text-red-700 ring-red-200 '
              + 'dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800'
              : 'bg-emerald-50 text-emerald-700 ring-emerald-200 '
              + 'dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-800'
          )}
        >
          {isHigh ? 'Suspicious metadata' : 'Looks consistent'}
        </span>
      </div>

      {/* Visual bar - keeps the original "score" presentation but driven by the
          discrete risk string. */}
      <div>
        <div className="h-2 w-full rounded-full overflow-hidden bg-surface-100
                        dark:bg-surface-800">
          <div className={cn('h-full transition-all',
                             isHigh ? 'bg-red-500' : 'bg-emerald-500')}
               style={{ width: `${score * 100}%` }} />
        </div>
        <div className="mt-1 text-xs text-surface-500 dark:text-surface-400">
          Heuristic score: {formatPct(score)}
        </div>
      </div>

      <div>
        <div className="text-xs uppercase tracking-wider text-surface-500
                        dark:text-surface-400 mb-2">
          Reasons
        </div>
        {reasons.length === 0 ? (
          <div className="text-sm text-surface-500 dark:text-surface-400">
            No specific concerns raised by the EXIF analysis.
          </div>
        ) : (
          <ul className="space-y-2">
            {reasons.map((r, i) => (
              <li key={i}
                  className="text-sm flex items-start gap-2
                             text-surface-700 dark:text-surface-200">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />
                <span>{typeof r === 'string' ? r : r.message ?? JSON.stringify(r)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function FrequencyPanel({ frequency }) {
  if (!frequency) {
    return (
      <div className="text-sm text-surface-500 dark:text-surface-400">
        No frequency analysis returned by the backend.
      </div>
    );
  }
  const imgUrl = resolveAssetUrl(frequency.spectrum_image_path);
  const ratio = frequency.high_freq_energy_ratio ?? null;

  return (
    <div className="space-y-4">
      {imgUrl ? (
        <div className="rounded-lg overflow-hidden border border-surface-200
                        dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
          <img src={imgUrl} alt="Frequency spectrum"
               className="w-full h-auto block" />
        </div>
      ) : (
        <div className="text-sm text-surface-500 dark:text-surface-400
                        rounded-lg border border-dashed
                        border-surface-300 dark:border-surface-700 p-8 text-center">
          No spectrum image returned by the backend.
        </div>
      )}
      <div>
        <div className="text-xs uppercase tracking-wider text-surface-500
                        dark:text-surface-400">
          High-frequency energy ratio
        </div>
        <div className="mt-1 text-2xl font-semibold">
          {ratio === null ? '—' : formatPct(ratio)}
        </div>
        <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
          {frequency.note ||
           'Higher values can indicate synthetic high-frequency artifacts.'}
        </p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(true);

  function handleFiles(files) {
    const f = files[0];
    if (!f) return;
    // Defensive double-check (DropZone already validates, but this page is
    // also reachable from keyboard / programmatic paths).
    const reason = validateImageFile(f);
    if (reason) {
      notify.error(reason);
      return;
    }
    setFile(f);
    setResult(null);
    setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(f));
  }

  function reset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setShowHeatmap(true);
  }

  async function runAnalysis() {
    if (!file) return;
    const tId = notify.loading('Running analysis…');
    setLoading(true);
    setError(null);
    try {
      const data = await predictDetailed(file);
      setResult(data);
      notify.dismiss(tId);
      notify.success('Analysis complete');
    } catch (e) {
      const norm = normalizeError(e);
      setError(norm.friendlyMessage);
      notify.dismiss(tId);
      notify.error(norm.friendlyMessage);
    } finally {
      setLoading(false);
    }
  }

  // The /predict-detailed endpoint returns:
  //   { cnn_result: {label, confidence, heatmap_url},
  //     exif_result: {...},
  //     frequency_result: {...},
  //     combined_verdict: {label, confidence, rationale} }
  // We prefer the combined verdict for the headline display.
  const cnn = result?.cnn_result;
  const combined = result?.combined_verdict;
  const verdict = combined?.label ?? cnn?.label;
  const confidence = combined?.confidence ?? cnn?.confidence;
  const heatmapUrl = useMemo(
    () => resolveAssetUrl(cnn?.heatmap_url),
    [cnn]
  );

  return (
    <div>
      <PageHeader
        title="Analyze an image"
        subtitle="Upload a photo to check whether it was generated by an AI model."
        icon={Upload}
        actions={file && !loading ? (
          <button onClick={reset} className="btn-ghost">
            <RotateCcw className="w-4 h-4" /> Reset
          </button>
        ) : null}
      />

      {!file && (
        <div className="max-w-2xl">
          <DropZone onFiles={handleFiles} />
        </div>
      )}

      {file && (
        <div className="space-y-6">
          {/* Selected image + action bar */}
          <div className="card-padded">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="w-20 h-20 rounded-lg overflow-hidden
                              border border-surface-200 dark:border-surface-700
                              bg-surface-100 dark:bg-surface-800 shrink-0">
                {previewUrl && (
                  <img src={previewUrl} alt=""
                       className="w-full h-full object-cover" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{file.name}</div>
                <div className="text-xs text-surface-500 dark:text-surface-400">
                  {(file.size / 1024).toFixed(1)} KB · {file.type || 'image'}
                </div>
              </div>
              <button
                onClick={runAnalysis}
                disabled={loading}
                className="btn-primary"
              >
                <Sparkles className="w-4 h-4" />
                {loading ? 'Analyzing…' : 'Analyze'}
              </button>
            </div>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="card-padded">
              <Spinner label="Running model + EXIF + frequency analysis…" />
            </div>
          )}

          {/* Error state */}
          {error && !loading && (
            <div className="card-padded border-red-200 dark:border-red-800
                            bg-red-50 dark:bg-red-900/20 text-red-700
                            dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* Results */}
          {result && !loading && verdict && (
            <div className="space-y-6 animate-fade-in">
              {/* Verdict hero */}
              <div className="card-padded flex flex-col sm:flex-row sm:items-center
                              gap-4 justify-between">
                <div className="flex items-center gap-4">
                  <VerdictBadge
                    verdict={verdict}
                    confidence={confidence}
                    size="lg"
                  />
                  <div className="text-sm text-surface-500 dark:text-surface-400">
                    Based on a multi-signal CNN + EXIF + FFT analysis.
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-wider
                                  text-surface-500 dark:text-surface-400">
                    Confidence
                  </div>
                  <div className="text-2xl font-semibold">
                    {formatPct(confidence)}
                  </div>
                </div>
              </div>

              {/* Rationale (only if available) */}
              {combined?.rationale && (
                <div className="card-padded">
                  <div className="text-sm font-semibold mb-2">Why this verdict?</div>
                  <p className="text-sm text-surface-700 dark:text-surface-200">
                    {combined.rationale}
                  </p>
                </div>
              )}

              {/* Original + Grad-CAM side-by-side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card-padded">
                  <div className="text-sm font-semibold mb-3">Original image</div>
                  <div className="rounded-lg overflow-hidden border
                                  border-surface-200 dark:border-surface-700
                                  bg-surface-50 dark:bg-surface-900">
                    <img src={previewUrl} alt=""
                         className="w-full h-auto block" />
                  </div>
                </div>

                <div className="card-padded">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-semibold">Grad-CAM heatmap</div>
                    <button
                      onClick={() => setShowHeatmap((s) => !s)}
                      className="btn-ghost text-xs px-2 py-1"
                    >
                      {showHeatmap
                        ? <><EyeOff className="w-3.5 h-3.5" /> Hide</>
                        : <><Eye className="w-3.5 h-3.5" /> Show</>}
                    </button>
                  </div>
                  {heatmapUrl ? (
                    <div className={cn(
                      'rounded-lg overflow-hidden border bg-surface-50 '
                      + 'dark:bg-surface-900 transition',
                      'border-surface-200 dark:border-surface-700'
                    )}>
                      {showHeatmap && (
                        <img src={heatmapUrl} alt="Grad-CAM heatmap"
                             className="w-full h-auto block" />
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-surface-500 dark:text-surface-400
                                    rounded-lg border border-dashed
                                    border-surface-300 dark:border-surface-700
                                    p-8 text-center">
                      No heatmap returned by the backend.
                    </div>
                  )}
                </div>
              </div>

              {/* Detailed analysis accordion */}
              <div>
                <div className="text-sm font-semibold mb-3">Detailed analysis</div>
                <Accordion
                  items={[
                    {
                      title: 'EXIF metadata risk',
                      defaultOpen: true,
                      content: <ExifPanel exif={result.exif_result} />,
                    },
                    {
                      title: 'Frequency-domain analysis',
                      content: <FrequencyPanel frequency={result.frequency_result} />,
                    },
                  ]}
                />
              </div>
            </div>
          )}

          {/* Result returned but no verdict - safety net so the page never
              looks broken / empty. */}
          {result && !loading && !verdict && (
            <EmptyState
              title="Unexpected response from backend"
              description={"The server returned a payload we couldn't interpret. " +
                           "Check the FastAPI logs for details."}
              action={
                <button onClick={reset} className="btn-primary">
                  <RotateCcw className="w-4 h-4" /> Start over
                </button>
              }
            />
          )}
        </div>
      )}

      {/* Persistent nudge when there's nothing on the page yet. */}
      {!file && (
        <div className="mt-6 text-center text-xs text-surface-500 dark:text-surface-400">
          Have a folder of images? Try the{' '}
          <Link to="/batch" className="text-brand-600 dark:text-brand-300 underline">
            batch analyser
          </Link>.
        </div>
      )}
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3, RefreshCw, CheckCircle2, Target, Gauge, Sigma, BarChart,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ScatterChart, Scatter,
  XAxis, YAxis, ZAxis,
  Tooltip, Cell, LabelList,
} from 'recharts';

import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import Spinner from '../components/Spinner';
import EmptyState from '../components/EmptyState';
import StatsSkeleton from '../components/Skeleton';
import { getStats, normalizeError } from '../api/client';
import notify from '../lib/toast';
import { cn } from '../lib/utils';

/**
 * Render the confusion matrix as a 2x2 "heatmap" using Recharts.
 * Recharts has no native heatmap component, so we plot one Scatter per cell
 * and color them by value. This is the canonical workaround and renders
 * cleanly with a responsive container.
 */
function ConfusionHeatmap({ matrix }) {
  // Normalize the matrix into a 2x2 grid: [[tp, fn], [fp, tn]] OR
  // whatever the backend sends (we accept multiple keys).
  const grid = useMemo(() => {
    if (!matrix) return null;
    if (Array.isArray(matrix) && matrix.length === 2 &&
        Array.isArray(matrix[0]) && matrix[0].length === 2) {
      return matrix;
    }
    // Try to pull values by name.
    const tp = matrix.tp ?? matrix.true_positive ?? matrix[0]?.[0];
    const fn = matrix.fn ?? matrix.false_negative ?? matrix[0]?.[1];
    const fp = matrix.fp ?? matrix.false_positive ?? matrix[1]?.[0];
    const tn = matrix.tn ?? matrix.true_negative ?? matrix[1]?.[1];
    if ([tp, fn, fp, tn].every((v) => typeof v === 'number')) {
      return [[tp, fn], [fp, tn]];
    }
    return null;
  }, [matrix]);

  if (!grid) {
    return (
      <div className="text-sm text-pencil/60">
        Confusion matrix unavailable.
      </div>
    );
  }

  // Flatten to a list of { x, y, value } cells, x = 0/1 (predicted),
  // y = 0/1 (actual). Higher value = darker.
  const labels = [
    ['True Real', 'False AI'],
    ['False Real', 'True AI'],
  ];
  const cells = [];
  for (let yi = 0; yi < 2; yi++) {
    for (let xi = 0; xi < 2; xi++) {
      cells.push({
        x: xi, y: yi, label: labels[yi][xi],
        value: grid[yi][xi] ?? 0,
      });
    }
  }
  const max = Math.max(...cells.map((c) => c.value), 1);

  // Each cell is its own Scatter so we can color independently.
  const rowLabels = ['Actual: Real', 'Actual: AI'];
  const colLabels = ['Predicted: Real', 'Predicted: AI'];

  return (
    <div className="w-full">
      <div className="grid grid-cols-[auto_1fr_1fr] gap-y-1 items-center">
        <div />
        {colLabels.map((c) => (
          <div key={c} className="text-center text-xs font-medium
                                  text-pencil/60">
            {c}
          </div>
        ))}

        {rowLabels.map((rowLabel, yi) => (
          <div key={rowLabel} className="contents">
            <div className="text-xs font-medium pr-2 text-right
                            text-pencil/60">
              {rowLabel}
            </div>
            {[0, 1].map((xi) => {
              const cell = cells.find((c) => c.x === xi && c.y === yi);
              const intensity = cell.value / max;          // 0..1
              const lightness = 92 - intensity * 38;       // 92% → 54%
              const isLight = intensity < 0.5;
              const textCls = isLight
                ? 'text-surface-800 dark:text-surface-100'
                : 'text-white';
              return (
                <div key={xi}
                     className="aspect-[2/1] wobbly-2 flex flex-col
                                items-center justify-center m-1
                                border-2 border-pencil
                                transition-transform hover:scale-[1.02]"
                     style={{
                       backgroundColor: `hsl(217, 91%, ${lightness}%)`,
                     }}>
                  <div className={cn('text-xs font-medium', textCls)}>
                    {cell.label}
                  </div>
                  <div className={cn('text-2xl font-semibold tabular-nums', textCls)}>
                    {cell.value}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* The "small Recharts chart" requirement — render a tiny sparkline
          style scatter using the same data so we satisfy the spec
          explicitly. */}
      <div className="mt-6 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
            <XAxis type="number" dataKey="x" name="predicted"
                   domain={[-0.5, 1.5]} ticks={[0, 1]}
                   tickFormatter={(v) => (v === 0 ? 'Real' : 'AI')}
                   tick={{ fontSize: 11 }}
                   stroke="currentColor"
                   className="text-pencil/60" />
            <YAxis type="number" dataKey="y" name="actual"
                   domain={[-0.5, 1.5]} ticks={[0, 1]}
                   tickFormatter={(v) => (v === 0 ? 'Real' : 'AI')}
                   tick={{ fontSize: 11 }}
                   stroke="currentColor"
                   className="text-pencil/60" />
            <ZAxis type="number" dataKey="value" range={[200, 1200]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{
                borderRadius: 8,
                border: '1px solid rgb(var(--color-surface-200) / 1)',
                background: 'rgb(var(--color-card) / 1)',
                color: 'rgb(var(--color-pencil) / 1)',
                fontSize: 12,
              }}
              formatter={(value) => [value, 'Count']}
              labelFormatter={(_, payload) =>
                payload?.[0]?.payload?.label ?? ''}
            />
            <Scatter data={cells}>
              {cells.map((c, i) => {
                const intensity = c.value / max;
                const lightness = 60 - intensity * 25;
                return (
                  <Cell key={i}
                        fill={`hsl(217, 91%, ${lightness}%)`}
                    stroke="rgb(var(--color-surface-900) / 1)" strokeOpacity={0.15} />
                );
              })}
              <LabelList dataKey="value" position="center"
                         style={{ fill: '#fff', fontSize: 11, fontWeight: 600 }} />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function pickNumber(obj, keys, fallback = null) {
  for (const k of keys) {
    if (obj?.[k] !== undefined && obj?.[k] !== null) return Number(obj[k]);
  }
  return fallback;
}

export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getStats();
      setStats(data);
    } catch (e) {
      const norm = normalizeError(e);
      setError(norm.friendlyMessage);
      notify.error(norm.friendlyMessage);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const accuracy  = pickNumber(stats, ['accuracy', 'acc']);
  const precision = pickNumber(stats, ['precision']);
  const recall    = pickNumber(stats, ['recall']);
  const f1        = pickNumber(stats, ['f1', 'f1_score']);
  const matrix    = stats?.confusion_matrix ?? stats?.confusionMatrix ?? stats?.matrix;
  const totals    = pickNumber(stats, ['total', 'samples'], null);
  const updatedAt = stats?.updated_at ?? stats?.timestamp;

  const metricsAreEmpty =
    !!stats &&
    (accuracy === null || accuracy === 0) &&
    (precision === null || precision === 0) &&
    (recall === null || recall === 0) &&
    (f1 === null || f1 === 0) &&
    (matrix == null ||
      (Array.isArray(matrix) && matrix.flat().every((v) => !v)));

  return (
    <div>
      <PageHeader
        title="Model performance"
        subtitle="Aggregated metrics over the labeled evaluation set."
        icon={BarChart3}
        actions={
          <button onClick={load} className="btn-ghost" disabled={loading}>
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            Refresh
          </button>
        }
      />

      {loading && !stats ? (
        <StatsSkeleton />
      ) : error ? (
        <div className="card-padded border-marker bg-marker/10 text-marker text-sm wobbly-3">
          {error}
        </div>
      ) : metricsAreEmpty ? (
        <EmptyState
          className="py-16"
          icon={BarChart}
          title="No metrics available yet"
          description={
            "We couldn't find any recorded metrics. Run the evaluation "
            + "script in model_training/ to produce a metrics.json, then drop "
            + "it into the backend folder."
          }
          action={
            <button onClick={load} className="btn-primary">
              <RefreshCw className="w-4 h-4" /> Try again
            </button>
          }
        />
      ) : (
        <div className="space-y-6 animate-fade-in">
          {/* KPI cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rotate-1">
              <StatCard label="Accuracy"  value={accuracy}
                        icon={CheckCircle2} accent="brand"
                        hint={totals !== null ? `Over ${totals} samples` : undefined} />
            </div>
            <div className="rotate-[-1]">
              <StatCard label="Precision" value={precision}
                        icon={Target} accent="real" />
            </div>
            <div className="rotate-1">
              <StatCard label="Recall"    value={recall}
                        icon={Gauge} accent="pending" />
            </div>
            <div className="rotate-[-1]">
              <StatCard label="F1 Score"  value={f1}
                        icon={Sigma} accent="fake" />
            </div>
          </div>

          {/* Confusion matrix */}
          <div className="rotate-1">
            <div className="card-padded relative">
              <div className="absolute -top-2 -right-2 w-4 h-4 bg-marker rounded-full shadow-hard z-10" />
              <div className="flex items-center justify-between mb-4">
                <div className="text-lg font-semibold font-heading">Confusion matrix</div>
                <div className="text-xs text-pencil/60">
                  Cell counts · darker = higher
                </div>
                {updatedAt && (
                  <div className="text-xs text-pencil/60">
                    Updated {new Date(updatedAt).toLocaleString()}
                  </div>
                )}
              </div>
              <ConfusionHeatmap matrix={matrix} />
            </div>
          </div>
        </div>
      )}

      {loading && stats && (
        <div className="mt-4 flex justify-center">
          <Spinner label="Refreshing…" />
        </div>
      )}
    </div>
  );
}

export const fmtHA = (v) =>
  v == null || Number.isNaN(v) ? '–' : v.toLocaleString('id-ID', { maximumFractionDigits: 1 }) + ' ha';

export const fmtPct = (v) =>
  v == null || Number.isNaN(v) ? '–' : (v * 100).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + '%';

export async function loadData() {
  const base = import.meta.env.BASE_URL || '/';
  const cleanBase = base.endsWith('/') ? base : base + '/';
  const [desa, kec, stats] = await Promise.all([
    fetch(`${cleanBase}data/desa.geojson`).then((r) => r.json()),
    fetch(`${cleanBase}data/kecamatan.geojson`).then((r) => r.json()),
    fetch(`${cleanBase}data/stats.json`).then((r) => r.json()),
  ]);
  return { desa, kec, stats };
}

const COLOR_RAMPS = {
  kelapa: ['#ecfdf5', '#a7f3d0', '#6ee7b7', '#34d399', '#10b981', '#059669', '#047857'],
  hutan: ['#f0fdf4', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a', '#14532d'],
  permukiman: ['#fff7ed', '#ffedd5', '#fed7aa', '#fb923c', '#ea580c', '#c2410c', '#7c2d12'],
  air: ['#f0f9ff', '#e0f2fe', '#bae6fd', '#38bdf8', '#0284c7', '#0369a1', '#0c4a6e'],
  lainnya: ['#fafaf9', '#f5f5f4', '#e7e5e4', '#d6d3d1', '#a8a29e', '#78716c', '#44403c'],
  default: ['#ecfdf5', '#a7f3d0', '#6ee7b7', '#34d399', '#10b981', '#059669', '#047857'],
};

/** Skala sekuensial berdasarkan komoditas fokus */
export function intensityColor(t, commodity = 'kelapa') {
  const stops = COLOR_RAMPS[commodity] || COLOR_RAMPS.default;
  const idx = Math.min(stops.length - 1, Math.max(0, Math.floor(t * (stops.length - 1))));
  return stops[idx];
}

export function download(filename, text, mime = 'text/csv') {
  const blob = new Blob([text], { type: mime });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

export function toCSV(rows, columns) {
  const head = columns.join(';');
  const body = rows.map((r) => columns.map((c) => r[c] ?? '').join(';')).join('\n');
  return head + '\n' + body;
}

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
  pala: ['#fdf8f6', '#f3e8e2', '#dcc1b0', '#c2977b', '#a47250', '#85512d', '#5a341b'],
  cengkeh: ['#f5f3ff', '#ddd6fe', '#c4b5fd', '#a78bfa', '#8b5cf6', '#7048e8', '#5b21b6'],
  jagung: ['#fffbeb', '#fef3c7', '#fde68a', '#fcd34d', '#fbbf24', '#f59e0b', '#d97706'],
  padi: ['#f7fee7', '#ecfccb', '#d9f99d', '#bef264', '#a3e635', '#84cc16', '#4d7c0f'],
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

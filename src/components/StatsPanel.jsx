import { useMemo } from 'react';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fmtHA, fmtPct, toCSV, download } from '../lib/data.js';

export default function StatsPanel({ stats, selected, focus, onSelectKec, onCollapse }) {
  const ctx = useMemo(() => {
    if (!stats) return null;
    if (selected?.type === 'desa') {
      const key = `${selected.nmkec}__${selected.nmdesa}`;
      const d = stats.desa[key];
      if (!d) return null;
      return {
        title: d.nmdesa,
        sub: `Desa · Kec. ${d.nmkec}`,
        total: d.total_ha,
        kelas: d.kelas,
        dominan: d.dominan,
      };
    }
    if (selected?.type === 'kecamatan') {
      const k = stats.kecamatan[selected.nmkec];
      if (!k) return null;
      return {
        title: `Kec. ${selected.nmkec}`,
        sub: `Kecamatan · ${k.n_desa} desa`,
        total: k.total_ha,
        kelas: k.kelas,
        dominan: k.dominan,
      };
    }
    return {
      title: 'Kabupaten Kepulauan Selayar',
      sub: 'Provinsi Sulawesi Selatan · 11 kecamatan · 88 desa',
      total: stats.kabupaten.total_ha,
      kelas: stats.kabupaten.kelas,
      dominan: 'kelapa',
    };
  }, [stats, selected]);

  const ranking = useMemo(() => {
    if (!stats) return [];
    const key = focus === 'dominan' ? 'kelapa' : focus;
    return Object.entries(stats.kecamatan)
      .map(([nmkec, v]) => ({ nmkec, ha: v.kelas[key] || 0, total: v.total_ha, n_desa: v.n_desa }))
      .sort((a, b) => b.ha - a.ha);
  }, [stats, focus]);

  if (!stats || !ctx) return <div className="p-5 text-sm text-stone-500">Memuat analisis statistik…</div>;

  const kelasArr = stats.kelas.map((c) => ({ ...c, ha: ctx.kelas[c.id] || 0 }));
  const fokusArr = ['kelapa', 'pala', 'cengkeh', 'jagung', 'padi'].map((id) => {
    const c = stats.kelas.find((x) => x.id === id);
    return {
      id,
      name: c.label,
      ha: Math.round((ctx.kelas[id] || 0) * 10) / 10,
      fill: c.color,
    };
  });

  const activeFocusLabel = focus === 'dominan' ? 'Kelapa' : stats.kelas.find((c) => c.id === focus)?.label || focus;
  const activeFocusColor = stats.kelas.find((c) => c.id === (focus === 'dominan' ? 'kelapa' : focus))?.color || '#059669';
  const primaryCropArea = ctx.kelas[focus === 'dominan' ? 'kelapa' : focus] || 0;
  const primaryCropShare = primaryCropArea / (ctx.total || 1);

  const unduh = () => {
    const csv = toCSV(
      ranking.map((r) => ({
        kecamatan: r.nmkec,
        [`luas_${focus === 'dominan' ? 'kelapa' : focus}_ha`]: r.ha,
        total_wilayah_ha: Math.round(r.total),
        jumlah_desa: r.n_desa,
      })),
      ['kecamatan', `luas_${focus === 'dominan' ? 'kelapa' : focus}_ha`, 'total_wilayah_ha', 'jumlah_desa']
    );
    download(`monitoring_luas_${focus === 'dominan' ? 'kelapa' : focus}_selayar.csv`, csv);
  };

  return (
    <div className="thin-scroll h-full overflow-y-auto p-3.5 space-y-4 text-stone-800 text-xs">
      {/* 1. Header Wilayah Terpilih & Minimize */}
      <div className="border-b border-stone-200/80 pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-emerald-700 truncate">
            <svg className="h-3.5 w-3.5 shrink-0 text-emerald-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            <span className="truncate">{ctx.sub}</span>
          </div>
          {onCollapse && (
            <button
              onClick={onCollapse}
              title="Sembunyikan Panel Statistik"
              className="flex items-center gap-1 rounded-lg border border-stone-200 bg-white px-2 py-1 text-[11px] font-medium text-stone-500 hover:bg-stone-100 hover:text-stone-800 shadow-2xs transition shrink-0 ml-2"
            >
              <span>Minimize</span>
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          )}
        </div>
        <h2 className="mt-1 text-base font-bold text-stone-900 tracking-tight">{ctx.title}</h2>
      </div>

      {/* 2. Ringkasan Kartu Utama */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="rounded-2xl bg-gradient-to-br from-emerald-800 to-emerald-950 p-3.5 text-white shadow-sm ring-1 ring-black/5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-300">Total Luas Tutupan</p>
          <p className="mt-1 text-xl font-extrabold tracking-tight">{fmtHA(ctx.total)}</p>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-200/90">
            <span>Citra Sentinel-2 2025</span>
          </div>
        </div>

        <div className="rounded-2xl border border-stone-200/80 bg-white p-3.5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">{activeFocusLabel}</p>
            <span className="h-2 w-2 rounded-full" style={{ background: activeFocusColor }} />
          </div>
          <p className="mt-1 text-xl font-extrabold text-stone-900 tracking-tight">{fmtHA(primaryCropArea)}</p>
          <p className="mt-2 text-[11px] font-medium text-emerald-700">
            {fmtPct(primaryCropShare)} <span className="font-normal text-stone-500">dari tutupan</span>
          </p>
        </div>
      </div>

      {/* 3. 5 Mini Cards Komoditas */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400 mb-1.5">5 Komoditas Strategis</p>
        <div className="grid grid-cols-5 gap-1.5">
          {fokusArr.map((f) => (
            <div
              key={f.name}
              className="rounded-xl border border-stone-200/80 bg-white px-1.5 py-2 text-center shadow-xs transition hover:border-emerald-300 hover:shadow-sm overflow-hidden flex flex-col justify-between min-w-0"
            >
              <div>
                <div className="mx-auto h-2 w-2 rounded-full shadow-xs" style={{ background: f.fill }} />
                <p className="mt-1 truncate text-[10px] font-semibold text-stone-600">{f.name}</p>
              </div>
              <div className="mt-1">
                <p className="text-[11px] sm:text-xs font-bold text-stone-900 tabular-nums tracking-tighter whitespace-nowrap leading-none" title={`${f.ha.toLocaleString('id-ID')} ha`}>
                  {f.ha.toLocaleString('id-ID')}
                </p>
                <p className="text-[9px] text-stone-400 font-medium mt-0.5">ha</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Chart Komparasi 5 Komoditas */}
      <section className="rounded-2xl border border-stone-200/80 bg-white p-3.5 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-stone-700">
            Perbandingan Komoditas (Hektar)
          </h3>
          <span className="text-[10px] font-medium text-stone-400">Bar Chart</span>
        </div>
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fokusArr} layout="vertical" margin={{ left: 4, right: 12, top: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0eeee" />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#78716c' }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 11, fontWeight: 500, fill: '#44403c' }} />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-xl border border-stone-200 bg-stone-900/90 px-3 py-2 text-white shadow-xl backdrop-blur text-xs">
                        <div className="flex items-center gap-1.5 font-bold">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: data.fill }} />
                          <span>{data.name}</span>
                        </div>
                        <div className="mt-1 font-mono text-emerald-400 font-bold">
                          {data.ha.toLocaleString('id-ID')} ha
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="ha" radius={[0, 6, 6, 0]}>
                {fokusArr.map((entry) => (
                  <Cell key={`cell-${entry.name}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* 5. Komposisi Seluruh Kelas Tutupan */}
      <section className="rounded-2xl border border-stone-200/80 bg-white p-3.5 shadow-sm space-y-2.5">
        <h3 className="text-xs font-bold uppercase tracking-wider text-stone-700">Komposisi Seluruh Kelas</h3>
        <ul className="space-y-2 text-xs">
          {kelasArr.map((c) => {
            const max = Math.max(1, ...kelasArr.map((x) => x.ha));
            const share = c.ha / (ctx.total || 1);
            return (
              <li key={c.id}>
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 font-medium text-stone-700">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full shadow-xs" style={{ background: c.color }} />
                    {c.label}
                  </span>
                  <div className="flex items-center gap-2 text-stone-500">
                    <span className="font-mono">{c.ha.toLocaleString('id-ID')} ha</span>
                    <span className="w-12 text-right font-bold text-stone-800">{fmtPct(share)}</span>
                  </div>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-stone-100">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${(c.ha / max) * 100}%`, background: c.color }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {/* 6. Peringkat Kecamatan */}
      <section className="rounded-2xl border border-stone-200/80 bg-white p-3.5 shadow-sm space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-stone-700">
              Peringkat Kecamatan
            </h3>
            <p className="text-[11px] text-stone-400">Berdasarkan {activeFocusLabel}</p>
          </div>
          <button
            onClick={unduh}
            className="flex items-center gap-1.5 rounded-lg bg-stone-900 px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-xs transition hover:bg-emerald-700"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>CSV</span>
          </button>
        </div>

        <ol className="divide-y divide-stone-100 text-xs">
          {ranking.map((r, i) => {
            const max = ranking[0]?.ha || 1;
            const isCurrentlySelected = selected?.type === 'kecamatan' && selected?.nmkec === r.nmkec;
            return (
              <li key={r.nmkec}>
                <button
                  onClick={() => onSelectKec(r.nmkec)}
                  className={`block w-full rounded-xl p-2 text-left transition ${
                    isCurrentlySelected
                      ? 'bg-emerald-50/90 ring-1 ring-emerald-400'
                      : 'hover:bg-stone-50'
                  }`}
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium text-stone-800">
                      <b className="font-semibold text-stone-400 mr-1.5">{i + 1}.</b>
                      {r.nmkec}
                    </span>
                    <span className="font-mono font-bold text-stone-900">
                      {r.ha.toLocaleString('id-ID')} ha
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-stone-100">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${(r.ha / max) * 100}%`, background: activeFocusColor }}
                    />
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

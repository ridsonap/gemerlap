import { useMemo, useState } from 'react';

export default function Sidebar({
  level, setLevel, focus, setFocus, basemap, setBasemap,
  split, setSplit, opacity, setOpacity, stats, onPick, onResetView,
  onCollapse,
}) {
  const [q, setQ] = useState('');

  const results = useMemo(() => {
    if (!stats || q.trim().length < 2) return [];
    const needle = q.trim().toLowerCase();
    const kecs = Object.keys(stats.kecamatan)
      .filter((k) => k.toLowerCase().includes(needle))
      .map((k) => ({ level: 'kecamatan', nmkec: k, label: `Kec. ${k}` }));
    const desas = Object.values(stats.desa)
      .filter((d) => d.nmdesa.toLowerCase().includes(needle) || d.nmkec.toLowerCase().includes(needle))
      .slice(0, 8)
      .map((d) => ({ level: 'desa', nmkec: d.nmkec, nmdesa: d.nmdesa, label: `${d.nmdesa}, Kec. ${d.nmkec}` }));
    return [...kecs.slice(0, 4), ...desas].slice(0, 10);
  }, [q, stats]);

  const fokusOps = [
    { id: 'dominan', label: 'Komoditas dominan', color: '#059669' },
    ...(stats?.kelas.filter((c) => ['kelapa', 'pala', 'cengkeh', 'jagung', 'padi'].includes(c.id)) || []),
  ];

  const totalKabupatenHa = stats?.kabupaten?.total_ha || 1;

  return (
    <div className="thin-scroll flex h-full flex-col overflow-y-auto p-3.5 space-y-4 text-stone-800 text-xs">
      {/* 1. Header Sidebar & Tombol Minimize */}
      <div className="flex items-center justify-between border-b border-stone-200/80 pb-2.5">
        <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] text-stone-700">
          <svg className="h-4 w-4 text-emerald-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
            <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
            <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
            <line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" />
            <line x1="17" y1="16" x2="23" y2="16" />
          </svg>
          <span>Panel Kontrol</span>
        </div>
        {onCollapse && (
          <button
            onClick={onCollapse}
            title="Sembunyikan Panel"
            className="flex items-center gap-1 rounded-lg border border-stone-200 bg-white px-2 py-1 text-[11px] font-medium text-stone-500 hover:bg-stone-100 hover:text-stone-800 shadow-2xs transition"
          >
            <span>Minimize</span>
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        )}
      </div>

      {/* 2. LEVEL WILAYAH */}
      <section>
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Tampilan Batas</h3>
          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
            {level === 'desa' ? '88 Desa' : '11 Kecamatan'}
          </span>
        </div>
        <div className="mt-1.5 grid grid-cols-2 rounded-xl bg-stone-200/80 p-1">
          <button
            onClick={() => setLevel('kecamatan')}
            className={`flex items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-semibold transition ${
              level === 'kecamatan'
                ? 'bg-white text-emerald-800 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 21h18M5 21V7l7-4 7 4v14M9 10v4M15 10v4" />
            </svg>
            <span>Kecamatan</span>
          </button>
          <button
            onClick={() => setLevel('desa')}
            className={`flex items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-semibold transition ${
              level === 'desa'
                ? 'bg-white text-emerald-800 shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>Desa (88)</span>
          </button>
        </div>
      </section>

      {/* 3. FOKUS PEWARNAAN / TEMATIK */}
      <section>
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Pewarnaan Tematik</h3>
          <span className="text-[10px] text-stone-400">Choropleth</span>
        </div>
        <div className="mt-1.5 relative">
          <select
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            className="w-full appearance-none rounded-xl border border-stone-200 bg-white py-2 pl-3 pr-8 text-xs font-semibold text-stone-800 shadow-2xs outline-none transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
          >
            {fokusOps.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-stone-400">
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-stone-500">
          {focus === 'dominan'
            ? 'Poligon diwarnai sesuai tanaman komoditas terluas di wilayah.'
            : `Gradasi intensitas luas ${fokusOps.find(o => o.id === focus)?.label || focus}.`}
        </p>
      </section>

      {/* 4. BASEMAP & PERBANDINGAN CITRA */}
      <section className="space-y-2.5">
        <h3 className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Citra & Perbandingan</h3>
        
        {/* Basemap Switcher */}
        <div className="grid grid-cols-3 gap-1 rounded-xl bg-stone-200/80 p-1">
          {[
            {
              id: 'satellite',
              label: 'Satelit',
              icon: (
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                </svg>
              ),
            },
            {
              id: 'light',
              label: 'Terang',
              icon: (
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ),
            },
            {
              id: 'osm',
              label: 'OSM',
              icon: (
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                  <line x1="8" y1="2" x2="8" y2="18" />
                  <line x1="16" y1="6" x2="16" y2="22" />
                </svg>
              ),
            },
          ].map((b) => (
            <button
              key={b.id}
              onClick={() => setBasemap(b.id)}
              className={`flex items-center justify-center gap-1 rounded-lg py-1.5 text-xs font-semibold transition ${
                basemap === b.id
                  ? 'bg-white text-emerald-800 shadow-2xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              <span>{b.icon}</span>
              <span>{b.label}</span>
            </button>
          ))}
        </div>

        {/* Split View Toggle */}
        <div
          onClick={() => setSplit(!split)}
          className="flex cursor-pointer items-center justify-between rounded-xl border border-stone-200/80 bg-white p-2.5 shadow-2xs transition hover:border-emerald-300"
        >
          <div>
            <div className="text-xs font-bold text-stone-800">Split View</div>
            <div className="text-[10px] text-stone-500">Klasifikasi vs Citra Satelit</div>
          </div>
          <button
            type="button"
            className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              split ? 'bg-emerald-600' : 'bg-stone-300'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                split ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Slider Transparansi */}
        <div className="rounded-xl border border-stone-200/80 bg-white p-2.5 shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-xs font-semibold text-stone-700">
            <span>Transparansi Layer</span>
            <span className="font-mono text-emerald-700">{Math.round(opacity * 100)}%</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={0.95}
            step={0.05}
            value={opacity}
            onChange={(e) => setOpacity(+e.target.value)}
            className="w-full cursor-pointer accent-emerald-600"
          />
        </div>

        {/* Reset View Button */}
        <button
          onClick={onResetView}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-stone-200 bg-white py-1.5 text-xs font-semibold text-stone-600 shadow-2xs transition hover:border-emerald-400 hover:bg-emerald-50 hover:text-emerald-700"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
          <span>Pusatkan Peta</span>
        </button>
      </section>

      {/* 5. CARI WILAYAH */}
      <section>
        <h3 className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Pencarian Wilayah</h3>
        <div className="relative mt-1.5">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5 text-stone-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Cari desa / kecamatan…"
            className="w-full rounded-xl border border-stone-200 bg-white py-1.5 pl-8 pr-7 text-xs font-medium text-stone-800 shadow-2xs outline-none transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
          />
          {q && (
            <button
              onClick={() => setQ('')}
              className="absolute inset-y-0 right-0 flex items-center pr-2 text-stone-400 hover:text-stone-600"
            >
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        {results.length > 0 && (
          <ul className="mt-1.5 divide-y divide-stone-100 overflow-hidden rounded-xl border border-stone-200 bg-white shadow-lg text-xs">
            {results.map((r, i) => (
              <li key={i}>
                <button
                  onClick={() => {
                    onPick(r);
                    setQ('');
                  }}
                  className="flex w-full items-center justify-between px-2.5 py-1.5 text-left transition hover:bg-emerald-50"
                >
                  <span className="font-medium text-stone-700 truncate">{r.label}</span>
                  <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-stone-500">
                    {r.level}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 6. LEGENDA KELAS TUTUPAN */}
      <section>
        <div className="flex items-center justify-between">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Legenda Tutupan</h3>
          <span className="text-[10px] text-stone-400">9 Kategori</span>
        </div>
        <ul className="mt-1.5 space-y-1 rounded-xl border border-stone-200/80 bg-white p-2 shadow-2xs text-xs">
          {(stats?.kelas || []).map((c) => {
            const ha = stats?.kabupaten?.kelas?.[c.id] || 0;
            const pct = (ha / totalKabupatenHa) * 100;
            return (
              <li key={c.id} className="flex items-center justify-between rounded-lg px-1.5 py-0.5 transition hover:bg-stone-50">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full shadow-2xs ring-1 ring-black/10" style={{ background: c.color }} />
                  <span className="font-medium text-stone-700 truncate">{c.label}</span>
                </div>
                <span className="font-mono text-[10px] text-stone-400">
                  {pct.toFixed(1)}%
                </span>
              </li>
            );
          })}
        </ul>
        <div className="mt-2 rounded-xl border border-amber-200/80 bg-amber-50/70 p-2 text-[10px] leading-relaxed text-amber-900 flex items-start gap-1.5">
          <svg className="h-3.5 w-3.5 shrink-0 text-amber-700 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <div>
            <b>Model Klasifikasi:</b> Resolusi 10m Sentinel-2 Kepulauan Selayar.
          </div>
        </div>
      </section>
    </div>
  );
}

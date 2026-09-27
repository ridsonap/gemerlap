import { useEffect, useState } from 'react';
import MapView from './components/MapView.jsx';
import Sidebar from './components/Sidebar.jsx';
import StatsPanel from './components/StatsPanel.jsx';
import { loadData } from './lib/data.js';

export default function App() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [level, setLevel] = useState('kecamatan');
  const [focus, setFocus] = useState('dominan');
  const [basemap, setBasemap] = useState('satellite');
  const [split, setSplit] = useState(true);
  const [opacity, setOpacity] = useState(0.7);
  const [selected, setSelected] = useState(null);
  const [flyTo, setFlyTo] = useState(null);
  const [resetTick, setResetTick] = useState(0);
  const [mobileTab, setMobileTab] = useState('peta'); // peta | filter | data
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  useEffect(() => {
    loadData().then(setData).catch((e) => setErr(String(e)));
  }, []);

  // Trigger Leaflet resize saat tab atau status sidebar berubah
  useEffect(() => {
    const timer = setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 150);
    return () => clearTimeout(timer);
  }, [mobileTab, leftCollapsed, rightCollapsed]);

  const pick = (r) => {
    setLevel(r.level);
    if (r.level === 'desa') setSelected({ type: 'desa', nmkec: r.nmkec, nmdesa: r.nmdesa });
    else setSelected({ type: 'kecamatan', nmkec: r.nmkec });
    setFlyTo({ ...r, t: Date.now() });
    setMobileTab('peta');
  };

  const selectKec = (nmkec) => {
    setLevel('kecamatan');
    setSelected({ type: 'kecamatan', nmkec });
    setFlyTo({ level: 'kecamatan', nmkec, t: Date.now() });
  };

  return (
    <div className="flex h-full flex-col bg-stone-100 font-sans">
      {/* 1. Header Navigation Bar */}
      <header className="z-30 flex h-14 shrink-0 items-center justify-between border-b border-stone-200/80 bg-white/95 px-3.5 backdrop-blur-md sm:px-4">
        <div className="flex items-center gap-2.5">
          {/* Toggle Tombol Panel Kiri (Desktop) */}
          <button
            onClick={() => setLeftCollapsed(!leftCollapsed)}
            title={leftCollapsed ? 'Tampilkan Panel Kontrol' : 'Sembunyikan Panel Kontrol'}
            className="hidden md:flex h-8 w-8 items-center justify-center rounded-lg border border-stone-200 bg-stone-50 text-stone-600 hover:bg-stone-100 hover:text-stone-900 transition"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </button>

          {/* Logo SVG */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-700 text-white shadow-2xs">
            <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>

          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-bold text-stone-900 tracking-tight sm:text-[15px]">
                Gemerlap <span className="font-normal text-stone-500">· Kepulauan Selayar</span>
              </h1>
              <span className="hidden rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold text-emerald-800 sm:inline-block">
                SENTINEL-2
              </span>
            </div>
            <p className="text-[11px] text-stone-500 line-clamp-1">
              Gerakan Menanam Lima Juta Kelapa
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selected && (
            <button
              onClick={() => setSelected(null)}
              className="flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 shadow-2xs transition hover:bg-emerald-100 active:scale-95"
            >
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              <span>{selected.type === 'desa' ? `${selected.nmdesa}` : selected.nmkec}</span>
              <span className="hidden font-normal text-emerald-600 sm:inline">— reset</span>
            </button>
          )}

          {/* Toggle Tombol Panel Kanan (Desktop) */}
          <button
            onClick={() => setRightCollapsed(!rightCollapsed)}
            title={rightCollapsed ? 'Tampilkan Panel Statistik' : 'Sembunyikan Panel Statistik'}
            className="hidden lg:flex h-8 w-8 items-center justify-center rounded-lg border border-stone-200 bg-stone-50 text-stone-600 hover:bg-stone-100 hover:text-stone-900 transition"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="15" y1="3" x2="15" y2="21" />
            </svg>
          </button>
        </div>
      </header>

      {/* 2. Main Content Area */}
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {/* Panel Kiri: Pengaturan & Legenda (Compact & Collapsible) */}
        {!leftCollapsed && (
          <aside className="hidden w-64 shrink-0 border-r border-stone-200/80 bg-stone-50/90 backdrop-blur md:block transition-all duration-300">
            {data ? (
              <Sidebar
                level={level}
                setLevel={setLevel}
                focus={focus}
                setFocus={setFocus}
                basemap={basemap}
                setBasemap={setBasemap}
                split={split}
                setSplit={setSplit}
                opacity={opacity}
                setOpacity={setOpacity}
                stats={data.stats}
                onPick={pick}
                onResetView={() => setResetTick((t) => t + 1)}
                onCollapse={() => setLeftCollapsed(true)}
              />
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-xs text-stone-400">
                {err ? `Gagal memuat: ${err}` : 'Memuat data…'}
              </div>
            )}
          </aside>
        )}

        {/* Peta Interaktif Leaflet (Maksimal Luas) */}
        <main className={`relative min-w-0 flex-1 ${mobileTab === 'peta' ? '' : 'hidden md:block'}`}>
          {/* Tombol Floating untuk Membuka Kembali Panel Kiri jika Di-minimize */}
          {leftCollapsed && (
            <button
              onClick={() => setLeftCollapsed(false)}
              className="absolute left-3 top-3.5 z-20 hidden md:flex items-center gap-1.5 rounded-xl border border-stone-200/80 bg-white/95 px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-md backdrop-blur transition hover:bg-stone-50 active:scale-95"
            >
              <svg className="h-3.5 w-3.5 text-emerald-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
                <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
                <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
                <line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" />
                <line x1="17" y1="16" x2="23" y2="16" />
              </svg>
              <span>Panel Kontrol</span>
            </button>
          )}

          {/* Tombol Floating untuk Membuka Kembali Panel Kanan jika Di-minimize */}
          {rightCollapsed && (
            <button
              onClick={() => setRightCollapsed(false)}
              className="absolute right-14 top-3 z-20 hidden lg:flex items-center gap-1.5 rounded-xl border border-stone-200/80 bg-white/95 px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-md backdrop-blur transition hover:bg-stone-50 active:scale-95"
            >
              <svg className="h-3.5 w-3.5 text-emerald-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
              <span>Panel Data</span>
            </button>
          )}

          {data ? (
            <MapView
              desa={data.desa}
              kec={data.kec}
              stats={data.stats}
              level={level}
              opacity={opacity}
              split={split}
              basemap={basemap}
              focus={focus}
              selected={selected}
              onSelect={setSelected}
              flyTo={flyTo}
              resetTick={resetTick}
            />
          ) : (
            <div className="absolute inset-0 grid place-items-center bg-stone-100 text-xs font-medium text-stone-500">
              {err ? `Gagal memuat peta: ${err}` : 'Menyiapkan peta spasial…'}
            </div>
          )}

          {/* Floating Pill Indikator Split View */}
          {split && (
            <div className="pointer-events-none absolute left-1/2 top-3.5 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-stone-200/60 bg-stone-900/85 p-1 text-[11px] font-semibold text-white shadow-xl backdrop-blur-md">
              <span className="rounded-full bg-emerald-600/90 px-2.5 py-0.5 text-white shadow-2xs">
                Klasifikasi
              </span>
              <span className="px-2 py-0.5 text-stone-300">
                Citra Satelit
              </span>
            </div>
          )}

          {/* Tombol Cepat di Mobile */}
          <div className="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 gap-2 md:hidden">
            <button
              onClick={() => setSplit((v) => !v)}
              className="rounded-full border border-stone-200 bg-white/95 px-3.5 py-1.5 text-xs font-bold text-stone-800 shadow-lg backdrop-blur"
            >
              Split {split ? 'ON' : 'OFF'}
            </button>
            <button
              onClick={() => setLevel(level === 'desa' ? 'kecamatan' : 'desa')}
              className="rounded-full bg-emerald-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-lg shadow-emerald-900/30"
            >
              {level === 'desa' ? 'Kecamatan' : 'Desa (88)'}
            </button>
          </div>
        </main>

        {/* Panel Kanan: Analisis Statistik (Lebar Nyaman & Collapsible) */}
        {!rightCollapsed && (
          <aside className={`w-full shrink-0 border-l border-stone-200/80 bg-stone-50/90 sm:w-96 lg:w-[390px] ${mobileTab === 'data' ? '' : 'hidden lg:block'} transition-all duration-300`}>
            {data && (
              <StatsPanel
                stats={data.stats}
                selected={selected}
                focus={focus}
                onSelectKec={selectKec}
                onCollapse={() => setRightCollapsed(true)}
              />
            )}
          </aside>
        )}

        {/* Drawer Filter Mobile & Backdrop */}
        {mobileTab === 'filter' && (
          <div className="fixed inset-0 z-50 flex md:hidden">
            {/* Backdrop overlay */}
            <div
              onClick={() => setMobileTab('peta')}
              className="fixed inset-0 bg-stone-950/60 backdrop-blur-xs transition-opacity"
            />
            {/* Drawer content */}
            <div className="relative z-50 flex h-full w-80 max-w-[85%] flex-col bg-white shadow-2xl">
              <div className="flex h-12 items-center justify-between border-b border-stone-200 px-4">
                <span className="text-xs font-bold uppercase tracking-wider text-stone-600">Filter & Pengaturan</span>
                <button
                  onClick={() => setMobileTab('peta')}
                  className="rounded-lg p-1 text-stone-400 hover:text-stone-700"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                {data && (
                  <Sidebar
                    level={level}
                    setLevel={setLevel}
                    focus={focus}
                    setFocus={setFocus}
                    basemap={basemap}
                    setBasemap={setBasemap}
                    split={split}
                    setSplit={setSplit}
                    opacity={opacity}
                    setOpacity={setOpacity}
                    stats={data.stats}
                    onPick={pick}
                    onResetView={() => setResetTick((t) => t + 1)}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Bottom Navigation Bar Mobile */}
      <nav className="z-20 grid shrink-0 grid-cols-3 border-t border-stone-200/90 bg-white/95 backdrop-blur text-xs md:hidden">
        {[
          {
            id: 'peta',
            label: 'Peta',
            icon: (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                <line x1="8" y1="2" x2="8" y2="18" />
                <line x1="16" y1="6" x2="16" y2="22" />
              </svg>
            ),
          },
          {
            id: 'filter',
            label: 'Filter',
            icon: (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" />
                <line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />
                <line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" />
              </svg>
            ),
          },
          {
            id: 'data',
            label: 'Data',
            icon: (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            ),
          },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setMobileTab(item.id)}
            className={`flex flex-col items-center justify-center py-2 font-bold transition gap-0.5 ${
              mobileTab === item.id ? 'text-emerald-700 border-t-2 border-emerald-700 bg-emerald-50/40' : 'text-stone-500'
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

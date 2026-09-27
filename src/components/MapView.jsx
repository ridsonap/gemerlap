import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { intensityColor } from '../lib/data.js';

const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const OSM = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const LIGHT = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}';

const tile = (url, attribution) => L.tileLayer(url, { maxZoom: 19, attribution });

function classColor(stats, id) {
  return (stats.kelas.find((c) => c.id === id) || {}).color || '#999';
}

export default function MapView({ desa, kec, stats, level, opacity, split, basemap, focus, selected, onSelect, flyTo, resetTick }) {
  const boxRef = useRef(null);
  const mainDiv = useRef(null);
  const topWrapRef = useRef(null);
  const topDiv = useRef(null);
  const maps = useRef({});
  const [pos, setPos] = useState(50);
  const isDragging = useRef(false);
  const cbRef = useRef({ onSelect });
  cbRef.current.onSelect = onSelect;

  // Handler drag untuk split divider
  const startDrag = (e) => {
    isDragging.current = true;
    e.preventDefault();
  };

  useEffect(() => {
    const onMove = (e) => {
      if (!isDragging.current || !boxRef.current) return;
      const rect = boxRef.current.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const newPos = Math.max(2, Math.min(98, ((clientX - rect.left) / rect.width) * 100));
      setPos(newPos);
    };
    const onUp = () => {
      isDragging.current = false;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchmove', onMove);
    window.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onUp);
    };
  }, []);

  // ---- init dua peta (bawah = pembanding/citra, atas = klasifikasi) ----
  useEffect(() => {
    const main = L.map(mainDiv.current, { zoomControl: false }).setView([-6.35, 120.75], 9);
    const top = L.map(topDiv.current, { zoomControl: false, attributionControl: false }).setView([-6.35, 120.75], 9);
    L.control.zoom({ position: 'topright' }).addTo(main);
    L.control.scale({ imperial: false }).addTo(main);

    // custom panes agar klasifikasi selalu di atas basemap tile
    for (const m of [main, top]) {
      m.createPane('classification').style.zIndex = 450;
      m.createPane('lines').style.zIndex = 460;
      m.createPane('clicks').style.zIndex = 470;
    }

    const M = (maps.current = {
      main, top,
      mainBase: {
        satellite: tile(ESRI, 'Esri World Imagery'),
        light: tile(LIGHT, 'Esri Light Gray Canvas'),
        osm: tile(OSM, '© OpenStreetMap'),
      },
      cmpBase: {
        satellite: tile(ESRI, 'Esri World Imagery'),
        light: tile(LIGHT, 'Esri Light Gray Canvas'),
      },
      topBase: {
        satellite: tile(ESRI, ''),
        light: tile(LIGHT, ''),
        osm: tile(OSM, ''),
      },
      classMain: L.geoJSON(null, { pane: 'classification' }),
      clickMain: L.geoJSON(null, { pane: 'clicks', style: { fillOpacity: 0, opacity: 0 } }),
      linesMain: L.geoJSON(null, { pane: 'lines' }),
      classTop: L.geoJSON(null, { pane: 'classification' }),
      linesTop: L.geoJSON(null, { pane: 'lines' }),
    });

    // sinkronisasi geser/zoom dua arah
    let guard = false;
    const link = (a, b) => a.on('move zoom', () => {
      if (guard) return;
      guard = true;
      try { b.setView(a.getCenter(), a.getZoom(), { animate: false }); } finally { guard = false; }
    });
    link(main, top);
    link(top, main);

    // lebar peta atas mengikuti wadah
    const ro = new ResizeObserver(() => {
      const w = boxRef.current?.clientWidth || 0;
      if (topDiv.current) topDiv.current.style.width = `${w}px`;
      try { main.invalidateSize(); } catch (_) {}
      try { top.invalidateSize(); } catch (_) {}
    });
    if (boxRef.current) ro.observe(boxRef.current);
    return () => { ro.disconnect(); main.remove(); top.remove(); };
  }, []);

  // ---- bangun layer klasifikasi + garis + tooltip + klik ----
  useEffect(() => {
    const M = maps.current;
    if (!M.main || !desa || !kec || !stats) return;
    const fc = level === 'desa' ? desa : kec;
    const dStats = stats.desa;
    const kStats = stats.kecamatan;

    const valOf = (p) => (level === 'desa'
      ? dStats[`${p.nmkec}__${p.nmdesa}`]?.kelas[focus] || 0
      : kStats[p.nmkec]?.kelas[focus] || 0);

    let maxVal = 1;
    if (focus !== 'dominan') maxVal = Math.max(1, ...fc.features.map(valOf));

    const fillOf = (p) => {
      if (focus === 'dominan') {
        const dom = level === 'desa' ? dStats[`${p.nmkec}__${p.nmdesa}`]?.dominan || p.dominan : kStats[p.nmkec]?.dominan;
        return classColor(stats, dom);
      }
      return intensityColor(valOf(p) / maxVal, focus);
    };

    const isSel = (p) => selected && (level === 'desa'
      ? selected.type === 'desa' && selected.nmkec === p.nmkec && selected.nmdesa === p.nmdesa
      : selected.type === 'kecamatan' && selected.nmkec === p.nmkec);

    const infoOf = (p) => (level === 'desa' ? dStats[`${p.nmkec}__${p.nmdesa}`] : { nmkec: p.nmkec, ...kStats[p.nmkec] });

    const popupOf = (p) => {
      const info = infoOf(p);
      if (!info?.kelas) return '';
      const top3 = Object.entries(info.kelas).sort((a, b) => b[1] - a[1]).slice(0, 3)
        .map(([k, v]) => `<div style="display:flex;justify-content:space-between;gap:12px;margin-top:2px;"><span>${stats.kelas.find((c) => c.id === k)?.label || k}:</span><b>${v.toLocaleString('id-ID')} ha</b></div>`).join('');
      return `<div style="min-width:180px">` +
        `<div style="font-weight:700;font-size:14px;color:#1c1917">${level === 'desa' ? `${p.nmdesa}` : p.nmkec}</div>` +
        `<div style="font-size:11px;color:#78716c;margin-bottom:8px">${level === 'desa' ? `Kec. ${p.nmkec}` : 'Kecamatan'} · Total ${(info.total_ha || 0).toLocaleString('id-ID')} ha</div>` +
        `<div style="font-size:12px;color:#44403c;border-top:1px solid #e7e5e4;padding-top:6px">${top3}</div>` +
        `<div style="font-size:10px;color:#059669;font-weight:600;margin-top:8px">Lihat data lengkap di panel kanan →</div>` +
        `</div>`;
    };

    const tooltipOf = (p) => {
      const info = infoOf(p);
      const name = level === 'desa' ? `${p.nmdesa}` : p.nmkec;
      const sub = level === 'desa' ? `Kec. ${p.nmkec}` : 'Kecamatan';
      const detail = focus === 'dominan'
        ? `Dominan: <b style="color:#a7f3d0">${stats.kelas.find(c => c.id === info?.dominan)?.label || info?.dominan || '-'}</b>`
        : `${stats.kelas.find(c => c.id === focus)?.label || focus}: <b style="color:#a7f3d0">${(valOf(p) || 0).toLocaleString('id-ID')} ha</b>`;
      return `<div style="font-size:12px;font-weight:700">${name}</div><div style="font-size:10px;opacity:0.8">${sub}</div><div style="font-size:11px;margin-top:3px">${detail}</div>`;
    };

    const pickOf = (p) => (level === 'desa'
      ? { type: 'desa', nmkec: p.nmkec, nmdesa: p.nmdesa }
      : { type: 'kecamatan', nmkec: p.nmkec });

    const styleClass = (f) => {
      const p = f.properties;
      const sel = isSel(p);
      return {
        fillColor: fillOf(p),
        fillOpacity: sel ? Math.min(0.95, opacity + 0.2) : opacity,
        color: sel ? '#064e3b' : '#ffffff',
        weight: sel ? 2.8 : 0.9,
        opacity: sel ? 1 : 0.85,
      };
    };

    for (const [key, sty] of [['classMain', styleClass], ['classTop', styleClass]]) {
      M[key].clearLayers();
      M[key].addData(JSON.parse(JSON.stringify(fc)));
      M[key].setStyle(sty);
    }

    for (const [key, extra] of [['linesMain', {}], ['linesTop', {}]]) {
      M[key].clearLayers();
      M[key].addData(fc);
      M[key].setStyle((f) => ({
        fill: false,
        fillOpacity: 0,
        color: '#1c1917',
        weight: level === 'desa' ? 0.6 : 1.5,
        opacity: 0.65,
        ...extra,
      }));
      M[key].eachLayer((l) => l.off('click'));
    }

    // lapisan klik transparan untuk sisi citra saat split
    M.clickMain.clearLayers();
    M.clickMain.addData(JSON.parse(JSON.stringify(fc)));
    M.clickMain.setStyle({ fillOpacity: 0, opacity: 0, weight: 0 });

    const bind = (layer) => layer.eachLayer((lyr) => {
      const p = lyr.feature.properties;
      lyr.bindPopup(popupOf(p));
      lyr.bindTooltip(tooltipOf(p), { sticky: true, className: 'gemerlap-map-tooltip', direction: 'top', offset: [0, -6] });
      lyr.off('click');
      lyr.on('click', () => cbRef.current.onSelect(pickOf(p)));
      lyr.on('mouseover', () => {
        if (layer === M.classMain || layer === M.classTop) {
          lyr.setStyle({
            fillColor: '#f59e0b',
            fillOpacity: Math.min(0.95, opacity + 0.25),
            color: '#ffffff',
            weight: 2.8,
            opacity: 1,
          });
          try { lyr.bringToFront(); } catch (_) {}
        }
      });
      lyr.on('mouseout', () => {
        if (layer === M.classMain || layer === M.classTop) {
          lyr.setStyle(styleClass(lyr.feature));
        }
      });
    });

    bind(M.classMain);
    bind(M.classTop);
    bind(M.clickMain);
  }, [desa, kec, stats, level, opacity, focus, selected]);

  // ---- atur basemap + mode split ----
  useEffect(() => {
    const M = maps.current;
    if (!M.main) return;
    const { main, top } = M;

    // Bersihkan semua layer dari kedua map
    Object.values(M.mainBase).forEach((l) => { if (main.hasLayer(l)) main.removeLayer(l); });
    Object.values(M.cmpBase).forEach((l) => { if (main.hasLayer(l)) main.removeLayer(l); });
    Object.values(M.topBase).forEach((l) => { if (top.hasLayer(l)) top.removeLayer(l); });

    [M.classMain, M.clickMain, M.linesMain].forEach((l) => { if (main.hasLayer(l)) main.removeLayer(l); });
    [M.classTop, M.linesTop].forEach((l) => { if (top.hasLayer(l)) top.removeLayer(l); });

    if (split) {
      // Split mode:
      // Bawah (main, terlihat di kanan): Citra satelit murni pembanding
      M.cmpBase.satellite.addTo(main);
      M.clickMain.addTo(main);
      M.clickMain.bringToFront();

      // Atas (top, terlihat di kiri): Basemap pilihan + layer klasifikasi
      const activeTopBase = M.topBase[basemap] || M.topBase.light;
      activeTopBase.addTo(top);
      M.classTop.addTo(top);
      M.linesTop.addTo(top);
    } else {
      // Non-split mode:
      // Basemap pilihan + klasifikasi penuh
      const activeBase = M.mainBase[basemap] || M.mainBase.satellite;
      activeBase.addTo(main);
      M.classMain.addTo(main);
      M.linesMain.addTo(main);
    }

    setTimeout(() => {
      try { main.invalidateSize(); } catch (_) {}
      try { top.invalidateSize(); } catch (_) {}
    }, 50);
  }, [basemap, split, level]);

  // ---- navigasi ----
  useEffect(() => {
    const M = maps.current;
    if (!M.main || !flyTo || !desa || !kec) return;
    const fc = flyTo.level === 'desa' ? desa : kec;
    const f = fc.features.find((x) => (flyTo.level === 'desa'
      ? x.properties.nmkec === flyTo.nmkec && x.properties.nmdesa === flyTo.nmdesa
      : x.properties.nmkec === flyTo.nmkec));
    if (f) {
      try {
        const b = L.geoJSON(f).getBounds();
        if (b.isValid() && mainDiv.current?.clientWidth > 0 && mainDiv.current?.clientHeight > 0) {
          M.main.flyToBounds(b.pad(0.2), { duration: 0.9 });
        }
      } catch (_) {}
    }
  }, [flyTo, desa, kec]);

  useEffect(() => {
    const M = maps.current;
    if (!M.main || !resetTick || !desa || !kec) return;
    try {
      const b = L.geoJSON(level === 'desa' ? desa : kec).getBounds();
      if (b.isValid() && mainDiv.current?.clientWidth > 0 && mainDiv.current?.clientHeight > 0) {
        M.main.flyToBounds(b.pad(0.05), { duration: 0.9 });
      }
    } catch (_) {}
  }, [resetTick]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div ref={boxRef} className="absolute inset-0 z-0 overflow-hidden select-none">
      {/* Peta Bawah (Citra Satelit Pembanding atau Peta Utama) */}
      <div ref={mainDiv} className="absolute inset-0" />

      {/* Peta Atas (Klasifikasi) dengan Clip Width mengikuti slider */}
      <div
        ref={topWrapRef}
        className="absolute inset-y-0 left-0 overflow-hidden border-r-2 border-white shadow-[0_0_24px_rgba(0,0,0,0.4)]"
        style={{ width: `${pos}%`, display: split ? 'block' : 'none' }}
      >
        <div ref={topDiv} className="absolute inset-y-0 left-0" />
      </div>

      {/* Kontrol Split View */}
      {split && (
        <div
          onMouseDown={startDrag}
          onTouchStart={startDrag}
          className="absolute inset-y-0 z-[500] flex w-12 -translate-x-1/2 cursor-ew-resize items-center justify-center group"
          style={{ left: `${pos}%` }}
        >
          {/* Handle visual tengah */}
          <div className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-white/90 bg-stone-900/90 text-white shadow-2xl backdrop-blur transition-transform group-hover:scale-105 active:scale-95">
            <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
              <polyline points="9 18 3 12 9 6" />
            </svg>
            <svg className="h-4.5 w-4.5 -ml-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
              <polyline points="15 18 21 12 15 6" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}

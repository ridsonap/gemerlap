# Gemerlap — Dashboard Monitoring Tanaman Kepulauan Selayar

Web dashboard monitoring luas tanaman (Kelapa, Pala, Cengkeh, Jagung, Padi + Hutan,
Permukiman, Air, Lainnya) di Kab. Kepulauan Selayar. Stack: **Vite + React + Leaflet +
Tailwind + Recharts**.

> **Status data: DUMMY.** Angka luas acak deterministik untuk prototipe UI.
> Ganti dengan hasil klasifikasi Sentinel-2 asli bila sudah tersedia.

## Jalankan

```bash
npm install
npm run dev      # buka http://localhost:5173
npm run build    # output ke dist/
npm run preview  # sajikan hasil build
```

## Regenerasi data dummy

```bash
pip install --break-system-packages pyshp
npm run gen:data   # baca Peta/*.shp -> public/data/*.geojson + stats.json
```

Sumber batas: `Peta/Desa 7301/Desa_7301.shp` (88 desa), `Peta/Kec 7301/kec_7301.shp` (11 kecamatan).

## Fitur

- Peta klasifikasi (choropleth) + overlay batas **Desa (88) / Kecamatan (11)**, atur transparansi
- **Split view** geser: kiri klasifikasi, kanan citra satelit Esri (tetap bisa klik & popup di kedua sisi)
- Basemap: Satelit / Terang / OSM; pewarnaan: dominan / intensitas per komoditas
- Panel statistik: KPI, donat komposisi, bar 5 komoditas, peringkat kecamatan, unduh CSV
- Cari desa/kecamatan (fly-to), klik poligon untuk detail, reset tampilan, responsif mobile

## Ganti ke data asli

1. Hasilkan raster klasifikasi Sentinel-2 (`kelas` 1–9 sesuai `classes.json`).
2. Hitung luas zonal per desa/kecamatan → timpa `public/data/stats.json`
   (struktur sama: `{ meta, kelas, kabupaten, kecamatan, desa }`, satuan hektar).
3. (Opsional) Sajikan raster sebagai tiles/COG dan tambahkan sebagai layer Leaflet.

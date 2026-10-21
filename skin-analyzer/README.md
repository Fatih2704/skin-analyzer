# SkinScan - Sistem Deteksi dan Analisis Kulit Wajah

Aplikasi web: unggah foto atau buka kamera, sistem menganalisis kulit wajah
(kecerahan, kilap minyak, tekstur, bintik) lalu memberi status
**Berminyak / Kusam / Kering / Normal** dan saran perawatan.

Metode: **Computer Vision (OpenCV/NumPy, opsional MediaPipe)** + **Rule-Based Method (If-Then)**.

## 1. Menjalankan

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Buka **http://127.0.0.1:5000**.

- Kamera browser hanya jalan di `localhost` atau **HTTPS**. Membuka lewat `http://192.168.x.x` dari HP
  akan memblokir kamera (tombol Unggah foto tetap bisa dipakai). Untuk uji di HP, pakai tunnel HTTPS (mis. ngrok).
- Halaman memuat Tailwind CSS dan Google Fonts dari CDN, jadi butuh internet saat pertama dibuka.
- Tes: `pytest -v`

### Opsional: detektor MediaPipe (Deep Learning)
Tanpa langkah ini sistem otomatis memakai OpenCV Haar Cascade (sudah cukup untuk demo).
```bash
pip install mediapipe
# unduh model ke ai_engine/models/blaze_face_short_range.tflite
curl -L -o ai_engine/models/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
```
Cek detektor aktif di `http://127.0.0.1:5000/api/health`.
(Catatan: jalur MediaPipe belum diuji oleh pembuat template ini; Haar sudah.)

## 2. Struktur proyek

```
skin-analyzer/
├── app.py                  Flask: halaman + POST /api/analyze
├── config.py               pengaturan server (ukuran upload, dll.)
├── ai_engine/
│   ├── analyzer.py         pipeline lengkap (pintu masuk)
│   ├── face_detector.py    [1] deteksi wajah
│   ├── feature_extractor.py[2] fitur: kecerahan, kilap, tekstur, bintik
│   ├── rule_engine.py      [3] aturan If-Then
│   ├── knowledge_base.py   isi saran perawatan
│   ├── thresholds.py       SEMUA angka ambang batas (tempat kalibrasi)
│   ├── visualizer.py       foto beranotasi
│   └── exceptions.py
├── templates/index.html
├── static/css/style.css
├── static/js/              main, camera, api, ui, image-utils
└── tests/
```

## 3. Alur sistem

1. Browser mengecilkan foto (maks 1280 px, JPEG) lalu `POST /api/analyze`.
2. Backend memvalidasi file, memprosesnya **di memori** (tidak disimpan).
3. Deteksi wajah -> ambil zona pipi + hidung -> filter warna kulit (YCrCb).
4. Hitung fitur:
   - kecerahan = rata-rata kanal V (HSV) piksel kulit
   - rasio kilap = % piksel V >= 240 dan S <= 45
   - tekstur = rata-rata |Laplacian| (10% tepi terkuat dibuang)
   - bintik = penyimpangan kemerahan (a*) / kegelapan (L) dari warna kulit sekitar
5. Rule engine (urutan prioritas, "first match wins"):

| Aturan | Jika | Maka |
|---|---|---|
| R1 | rasio kilap > 10% | Berminyak |
| R2 | kecerahan < 100 | Kusam |
| R3 | tekstur > 7 DAN kilap < 3% | Kering |
| R4 | selain di atas | Normal |

   Tingkat noda (terpisah): >= 3 bintik = Sedikit noda, >= 8 = Banyak noda.
6. Hasil JSON dirender oleh `ui.js`.

## 4. Format respons API

```json
{
  "success": true,
  "skin_type": {"key": "oily", "label": "Berminyak", "summary": "...", "rule_id": "R1"},
  "blemish": {"key": "few", "label": "Sedikit noda", "summary": "...", "count": 3},
  "metrics": [{"key": "shine", "label": "Kilap minyak", "value": 12.4,
               "display": "12.4%", "bar": 41.3, "marker": 33.3, "hint": "..."}],
  "rule_trace": [{"id": "R1", "if": "...", "then": "Berminyak", "actual": "...", "fired": true}],
  "recommendations": {"morning": [], "night": [], "ingredients": [], "avoid": [],
                      "lifestyle": [], "blemish_tips": []},
  "warnings": [],
  "face": {"x": 0, "y": 0, "w": 0, "h": 0, "detector": "haar"},
  "annotated_image": "data:image/jpeg;base64,...",
  "disclaimer": "..."
}
```
Error: `{"success": false, "error": {"code": "no_face", "message": "..."}}`
dengan kode `no_file`, `bad_format`, `invalid_image`, `no_face` (422), `too_large` (413), `server_error`.

## 5. Kalibrasi (WAJIB sebelum demo)

Threshold di `ai_engine/thresholds.py` baru disetel dengan citra sintetis dan satu foto contoh.
Langkah: kumpulkan 20-50 foto (berbagai warna kulit dan cahaya), catat nilai `metrics` dari API,
bandingkan dengan label yang kalian yakini, lalu geser angkanya. Tulis hasilnya di laporan.

## 6. Keterbatasan (cantumkan di laporan)

- Hanya pipi dan hidung yang dianalisis; dahi/dagu belum (butuh landmark, mis. MediaPipe FaceMesh).
- Kecerahan absolut bias terhadap warna kulit dan pencahayaan: kulit gelap atau foto redup bisa terbaca "Kusam".
- Kilap bergantung eksposur kamera; flash menggelembungkan rasio kilap.
- Tekstur sensitif terhadap noise kamera dan kompresi JPEG.
- Hanya pembeda warna/tekstur klasik, bukan model DL terlatih. Pengembangan: latih CNN
  (mis. MobileNet) pada dataset kulit berlabel dan gabungkan dengan aturan.
- Hasil adalah skrining visual, bukan diagnosis medis.

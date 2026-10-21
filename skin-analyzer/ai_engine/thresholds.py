"""
thresholds.py
=============
SATU-SATUNYA tempat untuk mengubah angka ambang batas (threshold) sistem.

Kenapa dipisah?
  - Angka-angka ini adalah "kalibrasi". Setiap kamera, pencahayaan, dan warna
    kulit memberi hasil berbeda, jadi kelompok kalian perlu menyetelnya
    dengan foto-foto uji milik sendiri.
  - Rule-Based Method hanya membandingkan fitur dengan angka di sini, sehingga
    mengubah aturan tidak perlu membongkar kode di tempat lain.

Satuan fitur:
  - brightness  : 0-255 (rata-rata kanal V pada HSV, hanya piksel kulit)
  - shine_ratio : persen piksel kulit yang tergolong "kilap" (specular)
  - texture     : rata-rata |Laplacian| (semakin besar = permukaan semakin kasar)
  - blemish_*   : jumlah bintik / persen luas bintik terhadap luas kulit
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    # --- Definisi "piksel kilap" (dipakai menghitung rasio kilap) ----------
    shine_v_min: int = 240          # piksel hampir putih (V >= nilai ini) ...
    shine_s_max: int = 45           # ... dan saturasi sangat rendah = pantulan cahaya (specular)

    # --- Aturan jenis kulit ------------------------------------------------
    oily_shine_ratio: float = 10.0  # IF rasio kilap > 10%           THEN Berminyak
    dull_brightness: float = 100.0  # IF kecerahan   < 100           THEN Kusam
    dry_texture: float = 7.0        # IF tekstur     > 7   ...
    dry_max_shine_ratio: float = 3.0  # ... AND kilap < 3%           THEN Kering

    # --- Deteksi bintik (jerawat / noda) -----------------------------------
    redness_delta: float = 9.0      # selisih kemerahan (kanal a*) vs sekitarnya
    dark_spot_delta: float = 28.0   # selisih kegelapan (kanal L) vs sekitarnya
    blemish_min_area: int = 6       # luas minimum bintik (piksel, citra wajah 256px)
    blemish_max_area: int = 160     # di atas ini dianggap bibir/bayangan, bukan bintik

    # --- Aturan tingkat noda -----------------------------------------------
    blemish_few: int = 3            # >= 3 bintik -> "Sedikit"
    blemish_many: int = 8           # >= 8 bintik -> "Banyak"

    # --- Kualitas foto (hanya untuk peringatan, bukan penentu hasil) -------
    min_face_px: int = 110          # lebar wajah minimal (piksel)
    min_face_brightness: float = 55.0
    max_shine_warning: float = 40.0


DEFAULT_THRESHOLDS = Thresholds()

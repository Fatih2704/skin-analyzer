"""
feature_extractor.py
====================
TAHAP 2 - Ekstraksi fitur visual dari area kulit wajah (Computer Vision).

Alur di file ini:
  1. extract_face_region()  : potong area wajah -> ubah ukuran standar (256 px)
                              -> buat "skin mask" (hanya piksel kulit yang dihitung)
  2. compute_features()     : hitung 4 fitur numerik dari skin mask:
        - brightness   : rata-rata kecerahan kulit (0-255)
        - shine_ratio  : persen piksel kilap/specular  (indikator minyak)
        - texture      : kekasaran permukaan           (indikator kering)
        - blemish_*    : jumlah & luas bintik          (jerawat / noda)

File ini HANYA menghasilkan angka. Keputusan "berminyak/kusam/..." diambil
oleh rule_engine.py, bukan di sini (pemisahan tanggung jawab).
"""
from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np

from .face_detector import FaceBox
from .thresholds import Thresholds

# Semua wajah diubah ke lebar yang sama agar angka fitur konsisten,
# apa pun resolusi foto aslinya.
NORMALIZED_WIDTH = 256

# ZONA ANALISIS (pecahan dari lebar/tinggi kotak wajah): (pusat_x, pusat_y, radius_x, radius_y)
# Hanya area yang PASTI kulit: pipi kiri, pipi kanan, dan hidung.
# Alasannya: tanpa landmark wajah, area dahi sering tertutup rambut/poni dan
# area mata/mulut menghasilkan tepi kuat yang merusak pengukuran tekstur & bintik.
# (Peningkatan: pakai MediaPipe FaceMesh agar dahi & dagu ikut dianalisis.)
ANALYSIS_ZONES = (
    (0.22, 0.62, 0.14, 0.13),   # pipi kiri
    (0.78, 0.62, 0.14, 0.13),   # pipi kanan
    (0.50, 0.54, 0.08, 0.11),   # hidung
)


# ====================================================================== #
#  Struktur data
# ====================================================================== #
@dataclass
class FaceRegion:
    """Area wajah yang sudah dinormalisasi + informasi untuk memetakan balik."""
    crop_bgr: np.ndarray    # potongan wajah (lebar 256 px)
    skin_mask: np.ndarray   # 255 = piksel kulit yang dianalisis, 0 = diabaikan
    roi_x: int              # posisi potongan pada citra asli
    roi_y: int
    roi_w: int
    roi_h: int
    scale: float            # piksel crop per piksel citra asli


@dataclass
class Features:
    """Hasil ekstraksi fitur; menjadi masukan untuk Rule Engine."""
    brightness: float       # 0-255
    shine_ratio: float      # persen
    texture: float          # rata-rata |Laplacian| (terpangkas)
    blemish_count: int
    blemish_ratio: float    # persen luas bintik terhadap luas kulit
    skin_pixels: int
    # Data tambahan hanya untuk visualisasi (tidak dipakai rule engine)
    shine_mask: np.ndarray = field(default=None, repr=False)
    blemish_points: List[Tuple[int, int, int, str]] = field(default_factory=list, repr=False)
    # setiap titik: (cx, cy, radius, jenis) pada koordinat crop; jenis "merah"/"gelap"


# ====================================================================== #
#  1. Menyiapkan area wajah + skin mask
# ====================================================================== #
def extract_face_region(image: np.ndarray, face: FaceBox) -> FaceRegion:
    h_img, w_img = image.shape[:2]

    # Potong sedikit tepi kotak wajah supaya latar & rambut tidak ikut terbaca
    x0 = max(0, int(face.x + 0.06 * face.w))
    x1 = min(w_img, int(face.x + 0.94 * face.w))
    y0 = max(0, int(face.y))
    y1 = min(h_img, int(face.y + face.h))
    roi = image[y0:y1, x0:x1]

    scale = NORMALIZED_WIDTH / roi.shape[1]
    crop = cv2.resize(roi, (NORMALIZED_WIDTH, max(1, int(roi.shape[0] * scale))),
                      interpolation=cv2.INTER_AREA)

    mask = _build_skin_mask(crop)
    return FaceRegion(crop, mask, x0, y0, x1 - x0, y1 - y0, scale)


def _build_skin_mask(crop: np.ndarray) -> np.ndarray:
    """Buat mask piksel kulit. Gabungan dua filter:
       (a) zona analisis (pipi + hidung)  -> membuang rambut, mata, mulut, latar
       (b) rentang warna kulit di ruang YCrCb -> membuang piksel non-kulit (+ isi lubang)
    """
    h, w = crop.shape[:2]

    # (a) Zona analisis
    zones = np.zeros((h, w), np.uint8)
    for fx, fy, frx, fry in ANALYSIS_ZONES:
        cv2.ellipse(zones, (int(fx * w), int(fy * h)), (int(frx * w), int(fry * h)),
                    0, 0, 360, 255, -1)

    # (b) Filter warna kulit (rentang klasik Cr 133-173, Cb 77-127)
    ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
    skin_color = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    value = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]
    skin_color[value < 40] = 0  # piksel sangat gelap = bukan kulit

    mask = cv2.bitwise_and(skin_color, zones)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    # PENTING - isi "lubang" pada mask. Pantulan cahaya (hampir putih) dan bintik
    # merah justru berada DI LUAR rentang warna kulit; kalau dibiarkan, keduanya
    # terbuang padahal itulah yang ingin kita ukur. Mengisi lubang membuat bercak
    # yang dikelilingi kulit tetap ikut dihitung, sedangkan rambut/alis yang
    # menempel di tepi zona tetap terbuang.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

    # Jaga-jaga: jika filter warna terlalu ketat (cahaya/warna tidak biasa),
    # pakai zona penuh agar analisis tetap berjalan.
    if np.count_nonzero(mask) < 0.25 * np.count_nonzero(zones):
        mask = zones
    return mask


# ====================================================================== #
#  2. Menghitung fitur
# ====================================================================== #
def compute_features(region: FaceRegion, th: Thresholds) -> Features:
    crop, mask = region.crop_bgr, region.skin_mask
    skin = mask > 0
    skin_pixels = int(np.count_nonzero(skin))
    if skin_pixels == 0:
        raise ValueError("Mask kulit kosong")

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    v, s = hsv[:, :, 2], hsv[:, :, 1]

    # --- Fitur 1: kecerahan = rata-rata kanal V pada piksel kulit -----------
    brightness = float(v[skin].mean())

    # --- Fitur 2: rasio kilap = piksel sangat terang & hampir putih ---------
    shine_mask = skin & (v >= th.shine_v_min) & (s <= th.shine_s_max)
    shine_ratio = float(shine_mask.sum()) / skin_pixels * 100.0

    # --- Fitur 3: tekstur = rata-rata |Laplacian| (kekasaran permukaan) -----
    # Laplacian menonjolkan perubahan intensitas tajam. Kulit halus -> nilai kecil,
    # kulit kasar/bersisik -> nilai besar. 10% tepi terkuat dibuang agar
    # garis tegas (bayangan hidung, alis yang lolos mask) tidak mendominasi.
    gray = cv2.GaussianBlur(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    inner = cv2.erode(mask, np.ones((5, 5), np.uint8)) > 0  # hindari tepi mask
    if inner.any():
        values = laplacian[inner]
        texture = float(values[values <= np.percentile(values, 90)].mean())
    else:
        texture = 0.0

    # --- Fitur 4: bintik (jerawat / noda) ------------------------------------
    points, spot_area = _detect_blemishes(crop, mask, inner, shine_mask, th)
    blemish_ratio = spot_area / skin_pixels * 100.0

    return Features(
        brightness=brightness,
        shine_ratio=shine_ratio,
        texture=texture,
        blemish_count=len(points),
        blemish_ratio=blemish_ratio,
        skin_pixels=skin_pixels,
        shine_mask=shine_mask,
        blemish_points=points,
    )


def _local_baseline(channel: np.ndarray, mask: np.ndarray, sigma: float = 12.0) -> np.ndarray:
    """Rata-rata lokal (blur berbobot mask) = 'warna kulit normal di sekitar'.
    Bintik adalah piksel yang menyimpang jauh dari baseline ini."""
    m = (mask > 0).astype(np.float32)
    num = cv2.GaussianBlur(channel * m, (0, 0), sigma)
    den = cv2.GaussianBlur(m, (0, 0), sigma) + 1e-6
    return num / den


def _detect_blemishes(crop, mask, inner, shine_mask, th: Thresholds):
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, a = lab[:, :, 0], lab[:, :, 1]

    # Piksel kilap (dan sekitarnya) dikeluarkan dari perhitungan baseline & kandidat,
    # supaya tepi pantulan cahaya tidak salah dibaca sebagai noda gelap.
    shine_zone = cv2.dilate(shine_mask.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    base_mask = (mask > 0) & ~shine_zone
    base_mask_u8 = base_mask.astype(np.uint8) * 255
    candidates_ok = inner & ~shine_zone

    redness = a - _local_baseline(a, base_mask_u8)          # positif = lebih merah dari sekitar
    darkness = _local_baseline(L, base_mask_u8) - L         # positif = lebih gelap dari sekitar

    points: List[Tuple[int, int, int, str]] = []
    total_area = 0
    for diff, delta, kind in ((redness, th.redness_delta, "merah"),
                              (darkness, th.dark_spot_delta, "gelap")):
        binary = ((diff > delta) & candidates_ok).astype(np.uint8) * 255
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, _, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for i in range(1, n):  # 0 = latar belakang
            area = int(stats[i, cv2.CC_STAT_AREA])
            bw, bh = int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])
            compact = 0.4 <= bw / max(bh, 1) <= 2.5  # bintik berbentuk bulat-ish, bukan garis
            if not (th.blemish_min_area <= area <= th.blemish_max_area and compact):
                continue
            cx, cy = centroids[i]
            radius = max(5, int(np.sqrt(area / np.pi) * 1.8))
            # Hindari hitung ganda: bintik merah biasanya juga lebih gelap dari sekitarnya
            if any((cx - px) ** 2 + (cy - py) ** 2 < (radius + pr) ** 2 * 0.64
                   for px, py, pr, _ in points):
                continue
            points.append((int(cx), int(cy), radius, kind))
            total_area += area
    return points, total_area

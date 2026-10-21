"""
visualizer.py
=============
Membuat foto beranotasi supaya pengguna bisa MELIHAT apa yang dideteksi sistem:
  - garis elips tipis  : zona kulit yang dianalisis (pipi & hidung)
  - warna kuning       : piksel kilap (minyak)
  - lingkaran merah    : bintik kemerahan (indikasi jerawat)
  - lingkaran biru     : noda gelap
Hasilnya dikirim ke browser sebagai data-URL base64 (tanpa menyimpan file).
"""
import base64

import cv2
import numpy as np

from .feature_extractor import ANALYSIS_ZONES, FaceRegion, Features

# Warna dalam format BGR (urutan OpenCV)
COLOR_AREA = (170, 190, 20)      # teal terang
COLOR_SHINE = (30, 190, 245)     # kuning
COLOR_REDNESS = (90, 90, 235)    # merah
COLOR_DARK = (230, 150, 70)      # biru


def draw_annotations(image: np.ndarray, region: FaceRegion, features: Features) -> np.ndarray:
    out = image.copy()
    x0, y0, rw, rh = region.roi_x, region.roi_y, region.roi_w, region.roi_h

    # 1) Tandai piksel kilap: perbesar mask kilap ke ukuran ROI asli lalu campur warna
    if features.shine_mask is not None and features.shine_mask.any():
        shine = cv2.resize(features.shine_mask.astype(np.uint8), (rw, rh),
                           interpolation=cv2.INTER_NEAREST).astype(bool)
        roi = out[y0:y0 + rh, x0:x0 + rw]
        tint = np.full_like(roi, COLOR_SHINE)
        roi[shine] = cv2.addWeighted(roi, 0.35, tint, 0.65, 0)[shine]

    # 2) Lingkaran bintik (koordinat crop -> koordinat citra asli)
    line = max(2, round(max(out.shape[:2]) / 400))
    for cx, cy, radius, kind in features.blemish_points:
        px = int(x0 + cx / region.scale)
        py = int(y0 + cy / region.scale)
        pr = int(radius / region.scale)
        cv2.circle(out, (px, py), pr, COLOR_REDNESS if kind == "merah" else COLOR_DARK,
                   line, cv2.LINE_AA)

    # 3) Garis zona analisis (pecahan zona dikalikan ukuran ROI asli)
    for fx, fy, frx, fry in ANALYSIS_ZONES:
        cv2.ellipse(out, (int(x0 + fx * rw), int(y0 + fy * rh)),
                    (int(frx * rw), int(fry * rh)), 0, 0, 360, COLOR_AREA, line, cv2.LINE_AA)
    return out


def to_data_url(image: np.ndarray, max_side: int = 900, quality: int = 85) -> str:
    """Kecilkan lalu ubah ke 'data:image/jpeg;base64,...' agar bisa langsung dipakai <img src>."""
    h, w = image.shape[:2]
    if max(h, w) > max_side:
        ratio = max_side / max(h, w)
        image = cv2.resize(image, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Gagal meng-encode gambar")
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")

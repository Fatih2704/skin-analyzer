"""
synthetic.py - Pembuat 'wajah' sintetis untuk pengujian tanpa foto asli.

Citra berupa kanvas warna kulit + noise + (opsional) pantulan cahaya & bintik.
Detektor wajah di-stub supaya selalu mengembalikan kotak yang menutupi seluruh
citra, sehingga yang diuji murni ekstraksi fitur + rule engine.
"""
import cv2
import numpy as np

from ai_engine.face_detector import FaceBox

SIZE = 400


class StubDetector:
    """Pengganti FaceDetector: selalu 'menemukan' wajah di seluruh citra."""
    def detect(self, image):
        h, w = image.shape[:2]
        return FaceBox(0, 0, w, h, 1.0, "stub")


class EmptyDetector:
    """Pengganti FaceDetector yang tidak pernah menemukan wajah."""
    def detect(self, image):
        return None


def make_face(skin_bgr=(150, 172, 222), noise=2.0, highlights=0, spots=0, seed=0):
    """skin_bgr   : warna dasar kulit (BGR)
       noise      : kekasaran tekstur (simpangan baku noise)
       highlights : banyaknya bercak pantulan cahaya (kilap)
       spots      : banyaknya bintik kemerahan"""
    rng = np.random.default_rng(seed)
    img = np.full((SIZE, SIZE, 3), skin_bgr, np.float32)

    # gradasi halus agar tidak 'terlalu rata'
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    img += (np.sin(xx / 60.0) * 3 + np.cos(yy / 70.0) * 3)[..., None]

    # tekstur kulit: noise yang sedikit diperhalus
    n = rng.normal(0, noise, (SIZE, SIZE, 1)).astype(np.float32)
    img += n

    img = np.clip(img, 0, 255).astype(np.uint8)

    # area target (sesuai ANALYSIS_ZONES) agar bercak jatuh di pipi/hidung
    centers = [(101, 248), (299, 248), (200, 232)]
    for i in range(highlights):
        cx, cy = centers[i % 3]
        ox, oy = rng.integers(-18, 18, 2)
        cv2.ellipse(img, (cx + int(ox), cy + int(oy)), (30, 22), 0, 0, 360, (250, 252, 252), -1)
    for i in range(spots):
        cx, cy = centers[i % 2]
        ox, oy = rng.integers(-35, 35, 2)
        cv2.circle(img, (cx + int(ox), cy + int(oy)), 4, (90, 90, 215), -1)
    return cv2.GaussianBlur(img, (0, 0), 0.8)

"""
face_detector.py
================
TAHAP 1 - Deteksi wajah (Computer Vision / Deep Learning).

Detektor dipilih bertingkat supaya proyek selalu bisa dijalankan:

  1. MediaPipe Face Detector (BlazeFace, model Deep Learning / CNN ringan)
     -> dipakai jika file model .tflite ada di folder ai_engine/models/
        (cara mengunduh ada di README, cukup sekali).
  2. OpenCV Haar Cascade (metode klasik)
     -> cadangan otomatis. Sudah ikut terpasang bersama opencv-python,
        jadi tidak perlu mengunduh apa pun.

Keluaran detektor: satu kotak wajah (FaceBox), yaitu wajah terbesar di foto.
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceBox:
    """Kotak pembatas wajah dalam koordinat piksel citra asli."""
    x: int
    y: int
    w: int
    h: int
    confidence: float
    method: str  # "mediapipe" atau "haar"


class FaceDetector:
    def __init__(self, mediapipe_model_path: Optional[str] = None):
        self.method = "haar"
        self._mp_detector = None
        self._mp = None

        # Cadangan: Haar Cascade bawaan OpenCV
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        self._haar = cv2.CascadeClassifier(cascade_path)
        if self._haar.empty():
            raise RuntimeError(f"Haar cascade tidak ditemukan di: {cascade_path}")

        # Utama (opsional): MediaPipe, hanya jika file modelnya ada
        if mediapipe_model_path and os.path.exists(mediapipe_model_path):
            try:
                self._load_mediapipe(mediapipe_model_path)
                self.method = "mediapipe"
            except Exception as exc:  # library tidak ada / versi tidak cocok
                logger.warning("MediaPipe gagal dimuat, memakai Haar Cascade: %s", exc)
        logger.info("Face detector aktif: %s", self.method)

    # ------------------------------------------------------------------ #
    def _load_mediapipe(self, model_path: str) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        options = vision.FaceDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            min_detection_confidence=0.5,
        )
        self._mp_detector = vision.FaceDetector.create_from_options(options)
        self._mp = mp

    def detect(self, bgr_image: np.ndarray) -> Optional[FaceBox]:
        """Kembalikan wajah terbesar, atau None bila tidak ada wajah."""
        box = None
        if self._mp_detector is not None:
            box = self._detect_mediapipe(bgr_image)
        if box is None:  # MediaPipe tidak aktif / tidak menemukan -> coba Haar
            box = self._detect_haar(bgr_image)
        return box

    # ------------------------------------------------------------------ #
    def _detect_mediapipe(self, bgr_image: np.ndarray) -> Optional[FaceBox]:
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._mp_detector.detect(mp_image)
        if not result.detections:
            return None
        best = max(result.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
        bb = best.bounding_box
        h_img, w_img = bgr_image.shape[:2]
        x, y = max(0, bb.origin_x), max(0, bb.origin_y)
        w, h = min(bb.width, w_img - x), min(bb.height, h_img - y)
        return FaceBox(x, y, w, h, float(best.categories[0].score), "mediapipe")

    def _detect_haar(self, bgr_image: np.ndarray) -> Optional[FaceBox]:
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # meratakan kontras agar deteksi lebih stabil
        min_side = int(min(gray.shape[:2]) * 0.15)
        faces = self._haar.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side)
        )
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # ambil yang terbesar
        return FaceBox(int(x), int(y), int(w), int(h), 0.8, "haar")

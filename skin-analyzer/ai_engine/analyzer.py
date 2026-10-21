"""
analyzer.py
===========
PINTU MASUK AI ENGINE. Merangkai seluruh pipeline:

   bytes gambar
      │  decode
      ▼
   [1] FaceDetector        -> kotak wajah          (face_detector.py)
      ▼
   [2] FeatureExtractor    -> angka fitur          (feature_extractor.py)
      ▼
   [3] RuleEngine (If-Then)-> jenis kulit + saran  (rule_engine.py)
      ▼
   [4] Visualizer          -> foto beranotasi      (visualizer.py)
      ▼
   dict hasil (siap di-jsonify oleh Flask)

Backend (app.py) cukup memanggil:  SkinAnalyzer().analyze(bytes_gambar)
"""
import logging
from typing import Dict, List, Optional

import cv2
import numpy as np

from . import visualizer
from .exceptions import InvalidImageError, NoFaceDetectedError
from .face_detector import FaceDetector
from .feature_extractor import Features, compute_features, extract_face_region
from .rule_engine import RuleEngine
from .thresholds import DEFAULT_THRESHOLDS, Thresholds

logger = logging.getLogger(__name__)

MAX_PROCESS_SIDE = 1280  # foto lebih besar dari ini dikecilkan dulu (lebih cepat)


class SkinAnalyzer:
    def __init__(self, thresholds: Thresholds = DEFAULT_THRESHOLDS,
                 mediapipe_model_path: Optional[str] = None,
                 detector: Optional[FaceDetector] = None):
        self.th = thresholds
        # `detector` boleh disuntik dari luar (berguna untuk pengujian)
        self.detector = detector or FaceDetector(mediapipe_model_path)
        self.rules = RuleEngine(thresholds)

    # ------------------------------------------------------------------ #
    def analyze(self, image_bytes: bytes) -> Dict:
        image = self._decode(image_bytes)
        return self.analyze_array(image)

    def analyze_array(self, image: np.ndarray) -> Dict:
        image = self._limit_size(image)

        # [1] Deteksi wajah
        face = self.detector.detect(image)
        if face is None:
            raise NoFaceDetectedError(
                "Pastikan wajah menghadap lurus ke kamera, cukup terang, "
                "dan tidak tertutup masker atau rambut."
            )

        # [2] Ekstraksi fitur
        region = extract_face_region(image, face)
        features = compute_features(region, self.th)

        # [3] Rule-Based Method
        decision = self.rules.run(features)

        # [4] Foto beranotasi
        annotated = visualizer.draw_annotations(image, region, features)

        return {
            "success": True,
            "skin_type": decision["skin_type"],
            "blemish": decision["blemish"],
            "metrics": self._build_metrics(features),
            "rule_trace": decision["rule_trace"],
            "recommendations": decision["recommendations"],
            "warnings": self._quality_warnings(face, features),
            "face": {"x": face.x, "y": face.y, "w": face.w, "h": face.h,
                     "detector": face.method},
            "annotated_image": visualizer.to_data_url(annotated),
            "disclaimer": decision["disclaimer"],
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def _decode(image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("File bukan gambar yang valid. Gunakan format JPG, PNG, atau WebP.")
        if min(image.shape[:2]) < 120:
            raise InvalidImageError("Resolusi foto terlalu kecil. Gunakan foto yang lebih besar.")
        return image

    @staticmethod
    def _limit_size(image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        if max(h, w) <= MAX_PROCESS_SIDE:
            return image
        ratio = MAX_PROCESS_SIDE / max(h, w)
        return cv2.resize(image, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)

    # ------------------------------------------------------------------ #
    def _build_metrics(self, f: Features) -> List[Dict]:
        """Ubah fitur mentah menjadi daftar metrik untuk bar di UI.
        bar     = posisi nilai pada skala 0-100
        marker  = posisi ambang batas aturan pada skala yang sama"""
        t = self.th

        def pct(value, scale_max):
            return round(min(max(value / scale_max, 0.0), 1.0) * 100, 1)

        return [
            {"key": "brightness", "label": "Kecerahan", "value": round(f.brightness, 1),
             "display": f"{f.brightness:.0f} / 255", "bar": pct(f.brightness, 255),
             "marker": pct(t.dull_brightness, 255),
             "hint": f"Di bawah {t.dull_brightness:.0f} dianggap kusam"},
            {"key": "shine", "label": "Kilap minyak", "value": round(f.shine_ratio, 1),
             "display": f"{f.shine_ratio:.1f}%", "bar": pct(f.shine_ratio, 30),
             "marker": pct(t.oily_shine_ratio, 30),
             "hint": f"Di atas {t.oily_shine_ratio:g}% dianggap berminyak"},
            {"key": "texture", "label": "Kekasaran tekstur", "value": round(f.texture, 1),
             "display": f"{f.texture:.1f}", "bar": pct(f.texture, t.dry_texture * 2),
             "marker": 50.0,
             "hint": f"Di atas {t.dry_texture:g} (dan tidak berkilap) dianggap kering"},
            {"key": "blemish", "label": "Bintik / noda", "value": f.blemish_count,
             "display": f"{f.blemish_count} titik", "bar": pct(f.blemish_count, t.blemish_many * 2),
             "marker": 50.0,
             "hint": f"{t.blemish_few}+ titik = sedikit noda, {t.blemish_many}+ = banyak noda"},
        ]

    def _quality_warnings(self, face, f: Features) -> List[str]:
        """Peringatan kualitas foto. Tidak mengubah hasil, hanya memberi tahu pengguna."""
        t, warnings = self.th, []
        if face.w < t.min_face_px:
            warnings.append("Wajah terlalu kecil di dalam foto. Dekatkan kamera agar hasil lebih akurat.")
        if f.brightness < t.min_face_brightness:
            warnings.append("Foto terlalu gelap. Hasil 'Kusam' bisa dipengaruhi cahaya, coba foto ulang di tempat terang.")
        if f.shine_ratio > t.max_shine_warning:
            warnings.append("Foto terlalu terang atau terkena flash, sehingga hasil kilap bisa berlebihan.")
        return warnings

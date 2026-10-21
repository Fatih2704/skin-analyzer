"""config.py - Pengaturan aplikasi Flask (bukan threshold AI; itu ada di ai_engine/thresholds.py)."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Batas ukuran upload: 8 MB. Browser juga mengecilkan foto sebelum dikirim,
    # jadi batas ini hanya pengaman tambahan.
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    # Format yang diterima backend
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}

    # Model MediaPipe (opsional). Jika file tidak ada, sistem otomatis memakai Haar Cascade.
    MEDIAPIPE_MODEL_PATH = os.path.join(BASE_DIR, "ai_engine", "models", "blaze_face_short_range.tflite")

    JSON_AS_ASCII = False  # agar teks Indonesia tidak diubah jadi \uXXXX
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

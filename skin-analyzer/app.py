"""
app.py
======
Backend web (Flask). Tugasnya TIPIS saja:
  1. Menyajikan halaman web (GET /)
  2. Menerima foto dari browser (POST /api/analyze)
  3. Menyerahkan foto ke AI engine, lalu membalas hasilnya sebagai JSON

Semua logika analisis ada di folder ai_engine/, bukan di sini.

Jalankan:   python app.py      lalu buka  http://127.0.0.1:5000
"""
import logging
import os

from flask import Flask, jsonify, render_template, request

from ai_engine import InvalidImageError, NoFaceDetectedError, SkinAnalyzer
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("skin-app")


def error_response(code: str, message: str, status: int):
    """Format error yang seragam, mudah dibaca oleh frontend."""
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Satu objek analyzer dipakai bersama (model dimuat sekali saat server menyala)
    analyzer = SkinAnalyzer(mediapipe_model_path=Config.MEDIAPIPE_MODEL_PATH)

    # ------------------------------ Halaman ------------------------------ #
    @app.get("/")
    def index():
        return render_template("index.html")

    # -------------------------------- API -------------------------------- #
    @app.get("/api/health")
    def health():
        """Untuk mengecek server hidup + detektor wajah yang aktif."""
        return jsonify({"status": "ok", "detector": analyzer.detector.method})

    @app.post("/api/analyze")
    def analyze():
        # 1) Ambil file dari form-data dengan nama field "image"
        file = request.files.get("image")
        if file is None or file.filename == "":
            return error_response("no_file", "Tidak ada foto yang dikirim.", 400)

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in Config.ALLOWED_EXTENSIONS:
            return error_response("bad_format", "Format tidak didukung. Gunakan JPG, PNG, atau WebP.", 400)

        # 2) Foto diproses di memori dan TIDAK disimpan ke disk (privasi)
        image_bytes = file.read()

        # 3) Jalankan AI engine
        try:
            result = analyzer.analyze(image_bytes)
        except InvalidImageError as exc:
            return error_response(exc.code, str(exc), 400)
        except NoFaceDetectedError as exc:
            return error_response(exc.code, str(exc), 422)
        except Exception:  # error tak terduga: catat di server, beri pesan umum ke pengguna
            logger.exception("Gagal menganalisis gambar")
            return error_response("server_error", "Terjadi kesalahan di server. Coba lagi sebentar.", 500)

        # 4) Kirim hasil sebagai JSON
        return jsonify(result)

    # ---------------------------- Penanganan error ------------------------ #
    @app.errorhandler(413)
    def too_large(_):
        return error_response("too_large", "Ukuran foto terlalu besar (maksimal 8 MB).", 413)

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return error_response("not_found", "Endpoint tidak ditemukan.", 404)
        return render_template("index.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    # host 0.0.0.0 agar bisa dibuka dari HP di jaringan WiFi yang sama.
    # CATATAN: kamera browser hanya jalan di localhost atau HTTPS (lihat README).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=Config.DEBUG)

"""exceptions.py - Error khusus agar backend bisa membalas pesan yang jelas ke pengguna."""


class SkinAnalysisError(Exception):
    """Kelas dasar semua error pada AI engine."""
    code = "analysis_error"


class InvalidImageError(SkinAnalysisError):
    """File yang dikirim bukan gambar yang valid / rusak."""
    code = "invalid_image"


class NoFaceDetectedError(SkinAnalysisError):
    """Tidak ada wajah yang terdeteksi pada foto."""
    code = "no_face"

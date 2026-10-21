/**
 * api.js
 * Satu-satunya file yang berbicara dengan backend (Fetch API / AJAX).
 * Frontend lain cukup memanggil analyzePhoto(blob).
 */

export class ApiError extends Error {
  constructor(message, code = "unknown") {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

/**
 * Kirim foto ke POST /api/analyze lalu kembalikan JSON hasil analisis.
 * Struktur JSON hasil dijelaskan di README (bagian "Format respons API").
 */
export async function analyzePhoto(blob) {
  // multipart/form-data: browser mengatur header & boundary-nya sendiri
  const form = new FormData();
  form.append("image", blob, "photo.jpg");

  let response;
  try {
    response = await fetch("/api/analyze", { method: "POST", body: form });
  } catch (_) {
    throw new ApiError("Tidak dapat terhubung ke server. Periksa koneksi lalu coba lagi.", "network");
  }

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    /* respons bukan JSON, ditangani di bawah */
  }

  if (!response.ok || !data || data.success !== true) {
    const err = data && data.error;
    throw new ApiError(
      (err && err.message) || "Analisis gagal. Coba lagi dengan foto lain.",
      (err && err.code) || "server_error"
    );
  }
  return data;
}

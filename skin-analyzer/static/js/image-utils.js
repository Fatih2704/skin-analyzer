/**
 * image-utils.js
 * Menyiapkan foto sebelum dikirim ke server:
 *   - memperbaiki orientasi foto HP (EXIF) agar wajah tidak miring
 *   - mengecilkan ukuran (sisi terpanjang maks. 1280 px) -> upload lebih cepat
 *   - mengubah semua format menjadi JPEG
 */

export const MAX_SIDE = 1280;
const MAX_INPUT_BYTES = 25 * 1024 * 1024; // batas file mentah dari perangkat

/** Memuat File/Blob menjadi gambar yang bisa digambar ke canvas. */
async function loadBitmap(blob) {
  // createImageBitmap + imageOrientation otomatis memutar foto sesuai EXIF
  if ("createImageBitmap" in window) {
    try {
      return await createImageBitmap(blob, { imageOrientation: "from-image" });
    } catch (_) {
      /* lanjut ke cara cadangan di bawah */
    }
  }
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("decode")); };
    img.src = url;
  });
}

/**
 * Menerima File dari <input type="file"> lalu mengembalikan { blob, url }.
 * `url` adalah object URL untuk ditampilkan di <img>; panggil URL.revokeObjectURL(url)
 * jika sudah tidak dipakai.
 */
export async function prepareImage(file) {
  if (!file.type.startsWith("image/")) {
    throw new Error("File yang dipilih bukan gambar. Pilih foto berformat JPG, PNG, atau WebP.");
  }
  if (file.size > MAX_INPUT_BYTES) {
    throw new Error("Ukuran file terlalu besar. Pilih foto di bawah 25 MB.");
  }

  let bitmap;
  try {
    bitmap = await loadBitmap(file);
  } catch (_) {
    throw new Error("Foto tidak dapat dibuka. Format HEIC dari iPhone belum didukung browser; gunakan JPG atau PNG.");
  }

  const w = bitmap.width ?? bitmap.naturalWidth;
  const h = bitmap.height ?? bitmap.naturalHeight;
  const ratio = Math.min(1, MAX_SIDE / Math.max(w, h));

  const canvas = document.createElement("canvas");
  canvas.width = Math.round(w * ratio);
  canvas.height = Math.round(h * ratio);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  if (bitmap.close) bitmap.close();

  const blob = await canvasToBlob(canvas);
  return { blob, url: URL.createObjectURL(blob) };
}

export function canvasToBlob(canvas, quality = 0.92) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Gagal memproses gambar."))),
      "image/jpeg",
      quality
    );
  });
}

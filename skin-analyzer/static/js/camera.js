/**
 * camera.js
 * Mengakses kamera lewat HTML5 MediaDevices API (navigator.mediaDevices.getUserMedia).
 *
 * Alur:
 *   start(videoEl)  -> minta izin kamera, tampilkan live preview di <video>
 *   capture()       -> ambil 1 frame dari video -> Blob JPEG
 *   stop()          -> matikan kamera (lampu indikator kamera padam)
 *
 * PENTING: getUserMedia hanya bekerja di "secure context":
 *   http://localhost, http://127.0.0.1, atau HTTPS.
 */
import { MAX_SIDE, canvasToBlob } from "./image-utils.js";

/** Mengubah error teknis dari browser menjadi pesan yang ramah pengguna. */
function friendlyError(err) {
  switch (err && err.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Izin kamera ditolak. Izinkan akses kamera lewat ikon gembok di address bar, lalu coba lagi.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "Kamera tidak ditemukan di perangkat ini. Gunakan tombol Unggah foto sebagai gantinya.";
    case "NotReadableError":
    case "AbortError":
      return "Kamera sedang dipakai aplikasi lain. Tutup aplikasi tersebut, lalu coba lagi.";
    default:
      return "Kamera tidak dapat dibuka. Gunakan tombol Unggah foto sebagai gantinya.";
  }
}

export class Camera {
  constructor() {
    this.stream = null;
    this.video = null;
  }

  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  async start(videoEl) {
    if (!window.isSecureContext || !Camera.isSupported()) {
      throw new Error(
        "Kamera hanya dapat dipakai lewat localhost atau HTTPS. Gunakan tombol Unggah foto sebagai gantinya."
      );
    }
    this.stop(); // pastikan tidak ada stream lama yang masih menyala

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",          // kamera depan
          width: { ideal: 1280 },
          height: { ideal: 960 },
        },
        audio: false,
      });
    } catch (err) {
      throw new Error(friendlyError(err));
    }

    this.video = videoEl;
    videoEl.srcObject = this.stream;
    await videoEl.play().catch(() => {});

    // Tunggu sampai ukuran video diketahui supaya capture() tidak menghasilkan gambar kosong
    if (!videoEl.videoWidth) {
      await new Promise((resolve) => videoEl.addEventListener("loadedmetadata", resolve, { once: true }));
    }
  }

  /** Ambil satu frame dari video sebagai Blob JPEG. */
  async capture() {
    const video = this.video;
    if (!video || !video.videoWidth) throw new Error("Kamera belum siap. Tunggu sebentar lalu coba lagi.");

    const ratio = Math.min(1, MAX_SIDE / Math.max(video.videoWidth, video.videoHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(video.videoWidth * ratio);
    canvas.height = Math.round(video.videoHeight * ratio);

    // Preview kamera ditampilkan secara cermin (mirror); hasil jepretan dibuat cermin juga
    // supaya sama dengan yang dilihat pengguna. Hasil analisis tidak terpengaruh.
    const ctx = canvas.getContext("2d");
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await canvasToBlob(canvas);
    return { blob, url: URL.createObjectURL(blob) };
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.video) this.video.srcObject = null;
  }
}

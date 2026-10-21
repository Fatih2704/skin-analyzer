/**
 * main.js - Titik masuk frontend & pengatur alur pengguna.
 *
 * ALUR:
 *   [idle] --Unggah/Kamera--> [preview] --Analisis kulit--> [scanning] --> [hasil]
 *             ^                    |                            |
 *             +----Ganti foto------+<-------- error ------------+
 *
 * File ini hanya "menyambung" modul lain:
 *   image-utils.js (siapkan foto) | camera.js (kamera) | api.js (server) | ui.js (tampilan)
 */
import { analyzePhoto, ApiError } from "./api.js";
import { Camera } from "./camera.js";
import { prepareImage } from "./image-utils.js";
import {
  clearError, renderResult, setDragOver, setPhotoMode, setScannerState,
  showError, showView, startScanningProgress,
} from "./ui.js";

const $ = (id) => document.getElementById(id);
const MIN_SCAN_MS = 3200;   // animasi scanning minimal tampil selama ini (agar terasa jelas)

const camera = new Camera();
let photo = null;     // foto yang sedang dipilih: { blob, url }
let busy = false;     // mencegah klik ganda saat proses berjalan

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ----------------------------------------------------------------------
   Kelola foto saat ini
   ---------------------------------------------------------------------- */
function setPhoto(newPhoto) {
  releasePhoto();
  photo = newPhoto;
  clearError();
  setScannerState("preview", photo.url);
}

function releasePhoto() {
  if (photo) URL.revokeObjectURL(photo.url);   // bebaskan memori
  photo = null;
}

function resetToStart() {
  camera.stop();
  releasePhoto();
  clearError();
  setScannerState("idle");
  showView("capture");
}

/* ----------------------------------------------------------------------
   Opsi A: UPLOAD FOTO
   ---------------------------------------------------------------------- */
async function handleFile(file) {
  if (!file || busy) return;
  camera.stop();
  try {
    setPhoto(await prepareImage(file));
  } catch (err) {
    showError("Foto tidak dapat dipakai", err.message);
  }
}

$("btn-upload").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", (e) => {
  handleFile(e.target.files[0]);
  e.target.value = "";            // agar memilih file yang sama dua kali tetap memicu event
});

// Seret & lepas foto ke bingkai
const scanner = $("scanner");
["dragenter", "dragover"].forEach((type) =>
  scanner.addEventListener(type, (e) => { e.preventDefault(); setDragOver(true); }));
["dragleave", "drop"].forEach((type) =>
  scanner.addEventListener(type, (e) => { e.preventDefault(); setDragOver(false); }));
scanner.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));

/* ----------------------------------------------------------------------
   Opsi B: KAMERA
   ---------------------------------------------------------------------- */
$("btn-camera").addEventListener("click", async () => {
  if (busy) return;
  clearError();
  try {
    setScannerState("camera");
    await camera.start($("video"));
  } catch (err) {
    setScannerState(photo ? "preview" : "idle", photo && photo.url);
    showError("Kamera tidak dapat dibuka", err.message);
  }
});

$("btn-shoot").addEventListener("click", async () => {
  try {
    const shot = await camera.capture();
    camera.stop();
    setPhoto(shot);
  } catch (err) {
    showError("Gagal mengambil foto", err.message);
  }
});

$("btn-cancel-camera").addEventListener("click", () => {
  camera.stop();
  setScannerState(photo ? "preview" : "idle", photo && photo.url);
});

$("btn-change").addEventListener("click", () => {
  releasePhoto();
  clearError();
  setScannerState("idle");
});

/* ----------------------------------------------------------------------
   Analisis: kirim ke backend sambil menampilkan animasi scanning
   ---------------------------------------------------------------------- */
$("btn-analyze").addEventListener("click", async () => {
  if (!photo || busy) return;
  busy = true;
  clearError();
  setScannerState("scanning", photo.url);
  const stopProgress = startScanningProgress();

  try {
    // Tunggu DUA hal: respons server DAN durasi minimal animasi
    const [result] = await Promise.all([analyzePhoto(photo.blob), sleep(MIN_SCAN_MS)]);
    stopProgress(true);
    await sleep(250);
    renderResult(result, photo.url);
    showView("result");
  } catch (err) {
    stopProgress();
    setScannerState("preview", photo.url);
    showError(errorTitle(err), err.message);
  } finally {
    busy = false;
  }
});

function errorTitle(err) {
  if (err instanceof ApiError) {
    if (err.code === "no_face") return "Wajah tidak terdeteksi";
    if (err.code === "network") return "Koneksi bermasalah";
    if (err.code === "invalid_image" || err.code === "bad_format") return "Foto tidak valid";
    if (err.code === "too_large") return "Foto terlalu besar";
  }
  return "Analisis gagal";
}

/* ----------------------------------------------------------------------
   Halaman hasil
   ---------------------------------------------------------------------- */
$("seg-original").addEventListener("click", () => setPhotoMode("original"));
$("seg-annotated").addEventListener("click", () => setPhotoMode("annotated"));
$("btn-restart").addEventListener("click", resetToStart);
$("btn-restart-bottom").addEventListener("click", resetToStart);

// Matikan kamera jika tab ditutup / pengguna berpindah halaman
window.addEventListener("pagehide", () => camera.stop());

// Kamera tidak tersedia? Beri tahu sejak awal, bukan setelah tombol ditekan.
if (!Camera.isSupported() || !window.isSecureContext) {
  $("btn-camera").title = "Kamera hanya tersedia lewat localhost atau HTTPS";
}

/**
 * ui.js
 * Semua manipulasi tampilan (DOM) ada di sini. Modul lain tidak menyentuh DOM langsung.
 *
 *   setScannerState()       -> ganti isi viewport: idle | camera | preview | scanning
 *   startScanningProgress() -> animasi teks langkah + progress bar saat scanning
 *   showView()              -> pindah antara tampilan "capture" dan "result"
 *   renderResult()          -> isi halaman hasil dari JSON backend
 */

const $ = (id) => document.getElementById(id);

/* ======================================================================
   1. VIEWPORT PEMINDAI
   ====================================================================== */

// Elemen apa yang terlihat pada setiap state
const STATE_LAYOUT = {
  idle:     { hint: true,  video: false, img: false, sweep: false, controls: null,       start: true  },
  camera:   { hint: false, video: true,  img: false, sweep: false, controls: "camera",   start: false },
  preview:  { hint: false, video: false, img: true,  sweep: false, controls: "preview",  start: true  },
  scanning: { hint: false, video: false, img: true,  sweep: true,  controls: "scanning", start: false },
};

export function setScannerState(state, imageUrl = null) {
  const layout = STATE_LAYOUT[state];
  $("scanner").dataset.state = state;

  $("idle-hint").hidden = !layout.hint;
  $("video").hidden = !layout.video;
  $("preview-img").hidden = !layout.img;
  $("scan-sweep").hidden = !layout.sweep;
  if (imageUrl) $("preview-img").src = imageUrl;

  for (const name of ["camera", "preview", "scanning"]) {
    $(`controls-${name}`).hidden = layout.controls !== name;
  }

  // Tombol "Unggah/Kamera" dikunci saat kamera aktif atau sedang scanning
  const lock = !layout.start;
  $("btn-upload").disabled = lock;
  $("btn-camera").disabled = lock;
}

export function showError(title, text) {
  $("error-title").textContent = title;
  $("error-text").textContent = text;
  $("error-box").hidden = false;
}

export function clearError() {
  $("error-box").hidden = true;
}

export function setDragOver(isOver) {
  $("scanner").classList.toggle("is-dragover", isOver);
}

/* ======================================================================
   2. ANIMASI TEKS SCANNING
   Langkah-langkah ini adalah gambaran dari pipeline sebenarnya di backend
   (deteksi wajah -> ekstraksi fitur -> rule-based).
   ====================================================================== */
const SCAN_STEPS = [
  "Mendeteksi wajah",
  "Menandai zona pipi dan hidung",
  "Mengukur kecerahan dan kilap",
  "Menilai tekstur dan bintik",
  "Menerapkan aturan perawatan",
];

/** Mulai animasi langkah. Mengembalikan fungsi untuk menghentikannya. */
export function startScanningProgress(stepMs = 750) {
  let i = 0;
  const text = $("scan-text");
  const bar = $("scan-bar");

  const tick = () => {
    text.textContent = SCAN_STEPS[Math.min(i, SCAN_STEPS.length - 1)];
    // Bar berhenti di 92% sampai hasil benar-benar datang
    bar.style.width = `${Math.min(92, ((i + 1) / SCAN_STEPS.length) * 92)}%`;
    i += 1;
  };
  bar.style.width = "0%";
  tick();
  const timer = setInterval(tick, stepMs);

  return (done = false) => {
    clearInterval(timer);
    if (done) bar.style.width = "100%";
  };
}

/* ======================================================================
   3. PINDAH TAMPILAN
   ====================================================================== */
export function showView(name) {
  $("view-capture").hidden = name !== "capture";
  $("view-result").hidden = name !== "result";
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "result") $("result-title").focus({ preventScroll: true });
}

/* ======================================================================
   4. RENDER HASIL
   ====================================================================== */

/** Helper kecil: buat elemen dengan teks (pakai textContent -> aman dari injeksi HTML). */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function fillList(id, items, className) {
  const list = $(id);
  list.replaceChildren(...(items || []).map((t) => el("li", className, t)));
}

export function renderResult(data, originalUrl) {
  const root = $("view-result");
  root.dataset.skin = data.skin_type.key;   // mengganti warna aksen lewat CSS

  // --- Status utama ---
  $("result-title").textContent = data.skin_type.label;
  $("result-summary").textContent = data.skin_type.summary;
  const blemish = $("result-blemish");   // label tebal + keterangan biasa
  blemish.replaceChildren(el("strong", "", `${data.blemish.label}:`), ` ${data.blemish.summary}`);

  // --- Peringatan kualitas foto ---
  const warnBox = $("warnings");
  warnBox.replaceChildren(...data.warnings.map((w) => el("p", "", w)));
  warnBox.hidden = data.warnings.length === 0;

  // --- Foto (asli vs beranotasi) ---
  const img = $("result-img");
  img.src = originalUrl;
  img.dataset.original = originalUrl;
  img.dataset.annotated = data.annotated_image;
  setPhotoMode("original");

  // --- Metrik + bar ---
  renderMetrics(data.metrics);

  // --- Rekomendasi ---
  const rec = data.recommendations;
  fillList("rec-morning", rec.morning);
  fillList("rec-night", rec.night);
  fillList("rec-ingredients", rec.ingredients);
  fillList("rec-avoid", rec.avoid);
  fillList("rec-lifestyle", rec.lifestyle);
  fillList("rec-blemish", rec.blemish_tips);
  $("blemish-block").hidden = !rec.blemish_tips || rec.blemish_tips.length === 0;

  // --- Jejak aturan (transparansi Rule-Based) ---
  renderTrace(data.rule_trace);

  $("disclaimer").textContent = data.disclaimer;
}

function renderMetrics(metrics) {
  const list = $("metrics");
  list.replaceChildren();
  const fills = [];

  for (const m of metrics) {
    const li = el("li");

    const head = el("div", "metric__head");
    head.append(el("span", "", m.label), el("span", "metric__value", m.display));

    const bar = el("div", "metric__bar");
    const fill = el("div", "metric__fill");
    fill.style.width = "0%";
    const marker = el("div", "metric__marker");
    marker.style.left = `${m.marker}%`;
    marker.title = "Batas aturan";
    bar.append(fill, marker);

    li.append(head, bar, el("p", "metric__hint", m.hint));
    list.append(li);
    fills.push([fill, m.bar]);
  }
  // Isi bar pada frame berikutnya supaya transisi lebar (animasi) berjalan
  requestAnimationFrame(() => requestAnimationFrame(() => {
    fills.forEach(([fill, value]) => { fill.style.width = `${value}%`; });
  }));
}

function renderTrace(trace) {
  $("rule-trace").replaceChildren(...trace.map((t) => {
    const li = el("li", t.fired ? "is-fired" : "");
    li.append(
      el("span", "trace__rule", `Aturan ${t.id}: jika ${t.if}, maka ${t.then}`),
      el("span", "trace__meta", `${t.actual}. ${t.fired ? "Terpenuhi, ini yang dipakai." : "Tidak terpenuhi."}`)
    );
    return li;
  }));
}

/** Ganti foto antara "original" dan "annotated". */
export function setPhotoMode(mode) {
  const img = $("result-img");
  const annotated = mode === "annotated";
  img.src = annotated ? img.dataset.annotated : img.dataset.original;

  $("seg-original").classList.toggle("is-active", !annotated);
  $("seg-annotated").classList.toggle("is-active", annotated);
  $("seg-original").setAttribute("aria-pressed", String(!annotated));
  $("seg-annotated").setAttribute("aria-pressed", String(annotated));
  $("photo-legend").hidden = !annotated;
}

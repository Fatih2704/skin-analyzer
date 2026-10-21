"""
rule_engine.py
==============
TAHAP 3 - Rule-Based Method (aturan If-Then).

Rule engine menerima angka fitur dari feature_extractor.py lalu memutuskan:
  (1) jenis kulit : Berminyak / Kusam / Kering / Normal
  (2) tingkat noda: Bersih / Sedikit noda / Banyak noda
  (3) rekomendasi perawatan (diambil dari knowledge_base.py)

Cara kerja jenis kulit = "first match wins":
  Aturan diperiksa berurutan dari prioritas tertinggi. Aturan pertama yang
  kondisinya terpenuhi menjadi keputusan, sisanya tidak diperiksa.
  Aturan terakhir (R4) selalu benar sehingga selalu ada hasil.

Setiap aturan memuat teks yang bisa dibaca manusia, sehingga UI dapat
menampilkan "kenapa hasilnya begini?" (explainable / transparan).
"""
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List

from .feature_extractor import Features
from .knowledge_base import BLEMISH_LEVELS, DISCLAIMER, SKIN_TYPES
from .thresholds import DEFAULT_THRESHOLDS, Thresholds


@dataclass
class Rule:
    id: str
    skin_type: str                                  # kunci pada knowledge_base.SKIN_TYPES
    text_if: str                                    # kalimat kondisi (boleh memuat {threshold})
    test: Callable[[Features, Thresholds], bool]    # kondisi sebenarnya
    actual: Callable[[Features, Thresholds], str]   # nilai aktual untuk ditampilkan


# ====================================================================== #
#  DAFTAR ATURAN JENIS KULIT (urutan = prioritas)
# ====================================================================== #
SKIN_TYPE_RULES: List[Rule] = [
    Rule(
        id="R1",
        skin_type="oily",
        text_if="Rasio kilap > {oily_shine_ratio}%",
        test=lambda f, t: f.shine_ratio > t.oily_shine_ratio,
        actual=lambda f, t: f"rasio kilap = {f.shine_ratio:.1f}%",
    ),
    Rule(
        id="R2",
        skin_type="dull",
        text_if="Rata-rata kecerahan < {dull_brightness}",
        test=lambda f, t: f.brightness < t.dull_brightness,
        actual=lambda f, t: f"kecerahan = {f.brightness:.0f}",
    ),
    Rule(
        id="R3",
        skin_type="dry",
        text_if="Tekstur > {dry_texture} DAN rasio kilap < {dry_max_shine_ratio}%",
        test=lambda f, t: f.texture > t.dry_texture and f.shine_ratio < t.dry_max_shine_ratio,
        actual=lambda f, t: f"tekstur = {f.texture:.1f}, rasio kilap = {f.shine_ratio:.1f}%",
    ),
    Rule(
        id="R4",
        skin_type="normal",
        text_if="Tidak ada aturan di atas yang terpenuhi",
        test=lambda f, t: True,  # aturan "else"
        actual=lambda f, t: "semua nilai dalam batas wajar",
    ),
]


# ====================================================================== #
#  RULE ENGINE
# ====================================================================== #
class RuleEngine:
    def __init__(self, thresholds: Thresholds = DEFAULT_THRESHOLDS):
        self.th = thresholds

    # -------------------- jenis kulit -------------------- #
    def classify_skin_type(self, f: Features) -> Dict:
        """Periksa aturan berurutan; simpan jejak (trace) setiap pemeriksaan."""
        params = asdict(self.th)
        trace = []
        decided = None
        for rule in SKIN_TYPE_RULES:
            fired = bool(rule.test(f, self.th))
            trace.append({
                "id": rule.id,
                "if": rule.text_if.format(**params),
                "then": SKIN_TYPES[rule.skin_type]["label"],
                "actual": rule.actual(f, self.th),
                "fired": fired,
            })
            if fired:
                decided = rule
                break  # first match wins
        return {"key": decided.skin_type, "rule_id": decided.id, "trace": trace}

    # -------------------- tingkat noda -------------------- #
    def classify_blemish(self, f: Features) -> Dict:
        """IF jumlah bintik >= batas THEN tingkat noda naik."""
        if f.blemish_count >= self.th.blemish_many:
            key = "many"
        elif f.blemish_count >= self.th.blemish_few:
            key = "few"
        else:
            key = "clear"
        return {"key": key}

    # -------------------- gabungan -------------------- #
    def run(self, f: Features) -> Dict:
        skin = self.classify_skin_type(f)
        blemish = self.classify_blemish(f)

        skin_kb = SKIN_TYPES[skin["key"]]
        blem_kb = BLEMISH_LEVELS[blemish["key"]]

        return {
            "skin_type": {
                "key": skin["key"],
                "label": skin_kb["label"],
                "summary": skin_kb["summary"],
                "rule_id": skin["rule_id"],
            },
            "blemish": {
                "key": blemish["key"],
                "label": blem_kb["label"],
                "summary": blem_kb["summary"],
                "count": f.blemish_count,
            },
            "recommendations": {
                **skin_kb["recommendations"],
                "blemish_tips": blem_kb["tips"],  # saran tambahan bila ada noda
            },
            "rule_trace": skin["trace"],
            "disclaimer": DISCLAIMER,
        }

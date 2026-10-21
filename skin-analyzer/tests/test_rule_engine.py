"""
Uji Rule Engine secara murni (tanpa gambar): cukup beri angka fitur, lihat keputusannya.
Jalankan:  pytest -v
"""
from ai_engine.feature_extractor import Features
from ai_engine.rule_engine import RuleEngine


def make_features(brightness=180, shine=2.0, texture=3.0, blemish=0):
    return Features(brightness=brightness, shine_ratio=shine, texture=texture,
                    blemish_count=blemish, blemish_ratio=0.0, skin_pixels=1000)


engine = RuleEngine()


def test_oily_when_shine_above_threshold():
    assert engine.run(make_features(shine=15))["skin_type"]["key"] == "oily"


def test_dull_when_brightness_below_threshold():
    assert engine.run(make_features(brightness=90))["skin_type"]["key"] == "dull"


def test_dry_when_rough_and_not_shiny():
    assert engine.run(make_features(texture=12, shine=1))["skin_type"]["key"] == "dry"


def test_normal_when_nothing_matches():
    assert engine.run(make_features())["skin_type"]["key"] == "normal"


def test_priority_oily_beats_dull():
    # Kilap tinggi DAN kecerahan rendah -> R1 (berminyak) menang karena prioritas lebih tinggi
    result = engine.run(make_features(shine=20, brightness=80))
    assert result["skin_type"]["key"] == "oily"
    assert result["skin_type"]["rule_id"] == "R1"


def test_rough_but_shiny_is_not_dry():
    # Tekstur kasar tetapi kilap 5% (>3%) -> bukan kering
    assert engine.run(make_features(texture=12, shine=5))["skin_type"]["key"] == "normal"


def test_blemish_levels():
    assert engine.run(make_features(blemish=0))["blemish"]["key"] == "clear"
    assert engine.run(make_features(blemish=3))["blemish"]["key"] == "few"
    assert engine.run(make_features(blemish=8))["blemish"]["key"] == "many"


def test_trace_stops_at_first_match():
    trace = engine.run(make_features(brightness=90))["rule_trace"]
    assert [t["id"] for t in trace] == ["R1", "R2"]       # R3, R4 tidak diperiksa
    assert [t["fired"] for t in trace] == [False, True]


def test_recommendations_present_for_every_type():
    for kw in (dict(shine=20), dict(brightness=80), dict(texture=12, shine=1), dict()):
        rec = engine.run(make_features(**kw))["recommendations"]
        assert rec["morning"] and rec["night"] and rec["avoid"]

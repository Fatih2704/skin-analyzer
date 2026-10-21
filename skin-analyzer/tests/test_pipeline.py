"""
Uji pipeline lengkap (ekstraksi fitur + rule engine + API) memakai wajah sintetis.
Detektor wajah diganti stub, jadi tes ini tidak bergantung pada foto asli.
"""
import io

import cv2
import pytest

from ai_engine import InvalidImageError, NoFaceDetectedError, SkinAnalyzer
from tests.synthetic import EmptyDetector, StubDetector, make_face

analyzer = SkinAnalyzer(detector=StubDetector())


def skin_key(image):
    return analyzer.analyze_array(image)["skin_type"]["key"]


def test_smooth_skin_is_normal():
    assert skin_key(make_face()) == "normal"


def test_shiny_skin_is_oily():
    assert skin_key(make_face(highlights=3)) == "oily"


def test_dark_image_is_dull():
    assert skin_key(make_face(skin_bgr=(45, 58, 85))) == "dull"


def test_rough_skin_is_dry():
    assert skin_key(make_face(noise=16)) == "dry"


def test_spots_are_counted():
    result = analyzer.analyze_array(make_face(spots=5))
    assert result["blemish"]["count"] >= 3
    assert result["blemish"]["key"] in ("few", "many")


def test_result_has_all_fields_for_frontend():
    result = analyzer.analyze_array(make_face())
    for key in ("skin_type", "blemish", "metrics", "rule_trace", "recommendations",
                "warnings", "annotated_image", "disclaimer"):
        assert key in result
    assert result["annotated_image"].startswith("data:image/jpeg;base64,")
    assert len(result["metrics"]) == 4


def test_no_face_raises():
    with pytest.raises(NoFaceDetectedError):
        SkinAnalyzer(detector=EmptyDetector()).analyze_array(make_face())


def test_invalid_bytes_raise():
    with pytest.raises(InvalidImageError):
        analyzer.analyze(b"ini bukan gambar")


# ---------------------------- Uji endpoint Flask ---------------------------- #
@pytest.fixture()
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def jpeg_bytes(img):
    ok, buf = cv2.imencode(".jpg", img)
    return io.BytesIO(buf.tobytes())


def test_api_requires_file(client):
    resp = client.post("/api/analyze")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "no_file"


def test_api_rejects_wrong_extension(client):
    resp = client.post("/api/analyze", data={"image": (io.BytesIO(b"x"), "file.txt")},
                       content_type="multipart/form-data")
    assert resp.status_code == 400


def test_api_rejects_fake_image(client):
    resp = client.post("/api/analyze", data={"image": (io.BytesIO(b"bukan gambar"), "a.jpg")},
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_image"


def test_api_blank_image_has_no_face(client):
    blank = cv2.cvtColor(cv2.UMat(480, 640, cv2.CV_8UC1, 128).get(), cv2.COLOR_GRAY2BGR)
    resp = client.post("/api/analyze", data={"image": (jpeg_bytes(blank), "blank.jpg")},
                       content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "no_face"


def test_health_and_index(client):
    assert client.get("/api/health").get_json()["status"] == "ok"
    assert client.get("/").status_code == 200

import io
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image
import pytest
import cv2
import numpy as np
from pymongo.errors import PyMongoError

import app as app_module
from app import app
from image_analysis import (
    analyze_face_landmarks,
    classify_skin_tone,
    detect_faces,
    estimate_face_shape,
    preprocess_image,
)
import storage as storage_module


def make_image(extension="PNG", size=(200, 200), color=(180, 140, 120)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=extension)
    output.seek(0)
    return output


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "UPLOAD_DIR", tmp_path)
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["recommendation_model"]["available"] is True
    assert body["recommendation_model"]["kind"] == "experimental_synthetic_neural_network"
    assert "mongodb" in body


def test_home_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"StyleAI" in response.data


def test_frontend_assets_are_served(client):
    assert client.get("/app.js").status_code == 200
    assert client.get("/style.css").status_code == 200


def test_valid_png_upload(client):
    response = client.post(
        "/api/upload",
        data={"photo": (make_image(), "portrait.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["uploaded"] is True
    assert body["width"] == 200
    assert body["height"] == 200
    assert body["face_count"] == 0
    assert body["landmark_face_count"] == 0
    assert body["detected"]["face_shape"] == "Unknown"
    assert body["face_landmarks"] == []
    assert body["photo_recommendations"]["available"] is False
    assert client.get(f"/api/uploads/{body['filename']}").status_code == 200


def test_upload_returns_face_landmarks_for_frontend_preview(client, monkeypatch):
    monkeypatch.setattr(app_module, "detect_faces", Mock(return_value=[{
        "x": 20,
        "y": 20,
        "width": 100,
        "height": 100,
    }]))
    monkeypatch.setattr(app_module, "classify_skin_tone", Mock(return_value={
        "skin_tone": "Medium",
        "confidence": 80,
    }))
    monkeypatch.setattr(app_module, "analyze_face_landmarks", Mock(return_value={
        "face_count": 1,
        "face_shape": "Oval",
        "landmarks": [{"x": 0.4, "y": 0.2}, {"x": 0.6, "y": 0.2}, {"x": 0.5, "y": 0.8}],
        "measurements": {"face_length_to_cheek_width": 1.4},
    }))

    response = client.post(
        "/api/upload",
        data={"photo": (make_image(), "portrait.png")},
        content_type="multipart/form-data",
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["detected"]["face_shape"] == "Oval"
    assert body["detected"]["skin_tone"] == "Medium"
    assert len(body["face_landmarks"]) == 3
    assert "verify or change it manually" in body["analysis_note"]
    photo_recommendations = body["photo_recommendations"]
    assert photo_recommendations["available"] is True
    assert photo_recommendations["color_palettes"]["Western"] == [
        "Emerald Green",
        "Royal Blue",
        "Burgundy",
    ]
    assert photo_recommendations["hairstyle"]["recommendation"]
    assert photo_recommendations["jewelry"]["earrings"] == "Hoops, studs, or drop earrings"


def test_rejects_missing_file(client):
    response = client.post("/api/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "No image file" in response.get_json()["error"]


def test_rejects_unsupported_extension(client):
    response = client.post(
        "/api/upload",
        data={"photo": (make_image(), "portrait.gif")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.get_json()["error"]


def test_rejects_extension_format_mismatch(client):
    response = client.post(
        "/api/upload",
        data={"photo": (make_image(), "portrait.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "does not match" in response.get_json()["error"]


def test_rejects_invalid_image(client):
    response = client.post(
        "/api/upload",
        data={"photo": (io.BytesIO(b"not an image"), "portrait.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "valid or safe-to-process image" in response.get_json()["error"]


def test_rejects_small_image(client):
    response = client.post(
        "/api/upload",
        data={"photo": (make_image(size=(50, 50)), "portrait.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "too small" in response.get_json()["error"]


def test_rejects_oversized_image(client):
    oversized = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))
    response = client.post(
        "/api/upload",
        data={"photo": (oversized, "portrait.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    assert "10 MB" in response.get_json()["error"]


def valid_profile():
    return {
        "height_inches": 64,
        "weight_kg": 58,
        "age": 24,
        "body_type": "Hourglass",
        "skin_tone": "Medium",
        "face_shape": "Oval",
        "occasion": "Office",
        "preferred_style": "Western",
        "hair_length": "Medium",
        "hair_texture": "Wavy",
    }


def test_recommendation_workflow_returns_renderable_data(client):
    response = client.post("/api/recommend", json=valid_profile())

    assert response.status_code == 200
    body = response.get_json()
    assert body["recommendation_method"] == "experimental_synthetic_neural_network"
    assert body["model_info"]["algorithm"] == "scikit-learn MLPClassifier (48, 24)"
    assert body["model_info"]["training_rows"] == 18000
    assert "not validated" in body["model_info"]["warning"]
    recommendations = body["recommendations"]
    assert recommendations["outfit"]["recommendation"]
    assert recommendations["outfit"]["basis"] == "Neural-network prototype"
    assert recommendations["color_palette"]["basis"] == "Neural-network prototype"
    assert recommendations["hairstyle"]["recommendation"]
    assert recommendations["earrings"]["recommendation"]
    assert recommendations["necklace"]["recommendation"]
    guide = body["styling_guide"]
    assert guide["colors_to_wear"]
    assert guide["colors_to_avoid"]
    assert guide["hairstyle_best"]
    assert guide["jewelry"]["earrings"]
    assert guide["jewelry"]["necklace"]
    assert guide["jewelry"]["bangles"]
    assert guide["jewelry"]["ring"]
    assert guide["accessories"]
    assert body["user_stats"]["bmi"] > 0
    assert body["mongodb"] == {"requested": False, "saved": False}


def test_saves_profile_only_after_explicit_opt_in(client, monkeypatch):
    class FakeCollection:
        document = None

        def insert_one(self, document):
            self.document = document
            return type("InsertResult", (), {"inserted_id": "test-record"})()

    collection = FakeCollection()
    monkeypatch.setattr(storage_module, "_collection", lambda: collection)
    profile = valid_profile()
    profile["save_to_mongodb"] = True

    response = client.post("/api/recommend", json=profile)

    assert response.status_code == 200
    assert response.get_json()["mongodb"] == {
        "requested": True,
        "saved": True,
        "record_id": "test-record",
    }
    assert collection.document["profile"]["face_shape"] == "Oval"
    assert "photo" not in collection.document


def test_reports_when_mongodb_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    storage_module._client_for_uri.cache_clear()
    profile = valid_profile()
    profile["save_to_mongodb"] = True

    response = client.post("/api/recommend", json=profile)

    assert response.status_code == 200
    database_result = response.get_json()["mongodb"]
    assert database_result["saved"] is False
    assert "MONGO_URI" in database_result["error"]


def test_reports_mongodb_save_errors_without_losing_recommendations(client, monkeypatch):
    class FailedCollection:
        def insert_one(self, document):
            assert isinstance(document, dict)
            raise PyMongoError("test connection failure")

    monkeypatch.setattr(storage_module, "_collection", lambda: FailedCollection())
    profile = valid_profile()
    profile["save_to_mongodb"] = True

    response = client.post("/api/recommend", json=profile)

    assert response.status_code == 200
    body = response.get_json()
    assert body["recommendations"]["outfit"]["recommendation"]
    assert body["mongodb"]["saved"] is False
    assert "Check the URI" in body["mongodb"]["error"]


def test_recommendation_changes_when_occasion_changes(client):
    profile = valid_profile()
    office = client.post("/api/recommend", json=profile).get_json()
    profile["occasion"] = "Party"
    party = client.post("/api/recommend", json=profile).get_json()

    assert office["recommendations"]["outfit"]["recommendation"] != party["recommendations"]["outfit"]["recommendation"]


def test_recommendation_palette_and_accessories_use_profile(client):
    profile = valid_profile()
    medium = client.post("/api/recommend", json=profile).get_json()
    profile["skin_tone"] = "Deep"
    profile["face_shape"] = "Round"
    deep_round = client.post("/api/recommend", json=profile).get_json()

    assert medium["styling_guide"]["colors_to_wear"] != deep_round["styling_guide"]["colors_to_wear"]
    assert medium["recommendations"]["earrings"]["recommendation"] != deep_round["recommendations"]["earrings"]["recommendation"]


@pytest.mark.parametrize(
    ("field", "values"),
    [
        ("body_type", ["Pear", "Apple", "Hourglass", "Rectangle", "Inverted Triangle"]),
        ("skin_tone", ["Fair", "Medium", "Wheatish", "Deep"]),
        ("face_shape", ["Round", "Oval", "Square", "Heart", "Diamond"]),
        ("occasion", ["Casual", "College", "Office", "Wedding", "Party"]),
        ("preferred_style", ["Western", "Traditional", "Indo-Western"]),
        ("hair_length", ["Short", "Medium", "Long"]),
        ("hair_texture", ["Straight", "Wavy", "Curly", "Coily"]),
    ],
)
def test_recommendation_handles_each_supported_category(client, field, values):
    profile = valid_profile()
    for value in values:
        profile[field] = value
        response = client.post("/api/recommend", json=profile)
        assert response.status_code == 200


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("height_inches", 20),
        ("weight_kg", float("nan")),
        ("body_type", "Unknown"),
        ("occasion", "Invalid"),
    ],
)
def test_recommendation_rejects_invalid_profile_values(client, field, value):
    profile = valid_profile()
    profile[field] = value

    response = client.post("/api/recommend", json=profile)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_preprocesses_image(tmp_path):
    source = tmp_path / "source.png"
    image = np.full((1200, 800, 3), (100, 120, 140), dtype=np.uint8)
    cv2.imwrite(str(source), image)

    processed = preprocess_image(source)

    assert processed.shape[:2] == (1024, 683)
    assert processed.dtype == np.uint8


def test_detect_faces_handles_blank_image():
    image = np.full((300, 300, 3), 180, dtype=np.uint8)

    faces = detect_faces(image)

    assert faces == []


def test_face_shape_uses_landmark_proportions():
    def landmarks(face_length, cheek_width, forehead_width, jaw_width):
        points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(468)]

        def set_point(index, x, y):
            points[index] = SimpleNamespace(x=x, y=y)

        set_point(10, 0.5, 0.1)
        set_point(152, 0.5, 0.1 + face_length)
        set_point(234, 0.5 - cheek_width / 2, 0.5)
        set_point(454, 0.5 + cheek_width / 2, 0.5)
        set_point(103, 0.5 - forehead_width / 2, 0.3)
        set_point(332, 0.5 + forehead_width / 2, 0.3)
        set_point(172, 0.5 - jaw_width / 2, 0.7)
        set_point(397, 0.5 + jaw_width / 2, 0.7)
        return points

    cases = [
        ((0.70, 0.60, 0.38, 0.40), "Round"),
        ((0.70, 0.60, 0.50, 0.56), "Square"),
        ((0.80, 0.70, 0.60, 0.40), "Heart"),
        ((0.80, 0.60, 0.42, 0.40), "Diamond"),
        ((0.90, 0.60, 0.58, 0.58), "Oval"),
    ]
    for dimensions, expected in cases:
        shape, measurements = estimate_face_shape(landmarks(*dimensions))
        assert shape == expected
        assert measurements["face_length_to_cheek_width"] > 0


def test_landmark_detection_returns_no_face_for_blank_image():
    image = np.full((300, 300, 3), 180, dtype=np.uint8)

    result = analyze_face_landmarks(image)

    assert result["face_count"] == 0
    assert result["face_shape"] == "Unknown"
    assert result["landmarks"] == []


def test_skin_tone_returns_unknown_when_no_skin_pixels():
    image = np.full((300, 300, 3), (10, 10, 10), dtype=np.uint8)
    face = {"x": 50, "y": 50, "width": 200, "height": 200}

    result = classify_skin_tone(image, face)

    assert result["skin_tone"] == "Unknown"
    assert result["confidence"] == 0.0


def test_skin_tone_returns_supported_category():
    image = np.full((300, 300, 3), (120, 160, 210), dtype=np.uint8)
    face = {"x": 50, "y": 50, "width": 200, "height": 200}

    result = classify_skin_tone(image, face)

    assert result["skin_tone"] in {"Fair", "Medium", "Wheatish", "Deep"}

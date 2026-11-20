import io

from PIL import Image
import pytest
import cv2
import numpy as np

import app as app_module
from app import app
from image_analysis import classify_skin_tone, detect_faces, preprocess_image


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
    assert response.get_json()["status"] == "ok"


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
    assert body["detected"]["face_shape"] == "Unknown"
    assert client.get(f"/api/uploads/{body['filename']}").status_code == 200


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
    assert body["recommendation_method"] == "rule-based"
    recommendations = body["recommendations"]
    assert recommendations["outfit"]["recommendation"]
    assert recommendations["outfit"]["basis"] == "Rule-based"
    assert recommendations["color_palette"]["basis"] == "Rule-based"
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


def test_recommendation_changes_when_occasion_changes(client):
    profile = valid_profile()
    office = client.post("/api/recommend", json=profile).get_json()
    profile["occasion"] = "Party"
    party = client.post("/api/recommend", json=profile).get_json()

    assert office["recommendations"]["outfit"]["recommendation"] != party["recommendations"]["outfit"]["recommendation"]


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

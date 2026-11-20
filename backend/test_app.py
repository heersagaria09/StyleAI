import io

from PIL import Image
import pytest
import cv2
import numpy as np

from app import app
from image_analysis import classify_skin_tone, detect_faces, preprocess_image


def make_image(extension="PNG", size=(200, 200), color=(180, 140, 120)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=extension)
    output.seek(0)
    return output


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


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
    assert body["detected"] is None


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


def test_rejects_invalid_image(client):
    response = client.post(
        "/api/upload",
        data={"photo": (io.BytesIO(b"not an image"), "portrait.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "valid image" in response.get_json()["error"]


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
    assert response.status_code == 400
    assert "10 MB" in response.get_json()["error"]


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

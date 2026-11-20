import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app = Flask(__name__)
CORS(app)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/upload")
def upload_photo():
    uploaded = request.files.get("photo")
    if uploaded is None:
        return jsonify({"error": "No image file was provided."}), 400

    filename = uploaded.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported file type. Use JPG, PNG, or WEBP."}), 400

    uploaded.stream.seek(0, os.SEEK_END)
    size = uploaded.stream.tell()
    uploaded.stream.seek(0)
    if size == 0:
        return jsonify({"error": "The uploaded image is empty."}), 400
    if size > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Image exceeds the 10 MB size limit."}), 400

    try:
        with Image.open(uploaded.stream) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        return jsonify({"error": "The file is not a valid image."}), 400

    uploaded.stream.seek(0)
    try:
        with Image.open(uploaded.stream) as image:
            image_format = image.format
            width, height = image.size
        if image_format not in ALLOWED_FORMATS:
            return jsonify({"error": "Unsupported image format."}), 400
        if width < 100 or height < 100:
            return jsonify({"error": "Image is too small. Use at least 100 x 100 pixels."}), 400
    except (UnidentifiedImageError, OSError):
        return jsonify({"error": "The file could not be decoded."}), 400

    stored_name = f"{uuid.uuid4().hex}.{extension}"
    stored_path = UPLOAD_DIR / stored_name
    uploaded.stream.seek(0)
    uploaded.save(stored_path)

    return jsonify({
        "uploaded": True,
        "filename": stored_name,
        "width": width,
        "height": height,
        "size_bytes": size,
        "detected": None,
    })


@app.get("/api/uploads/<filename>")
def uploaded_photo(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

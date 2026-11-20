import os
import uuid
from pathlib import Path

import cv2
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

from image_analysis import classify_skin_tone, detect_faces, preprocess_image
from recommendation_model import get_recommendations, model_status
from style_catalog import get_body_type_guide, get_color_avoidance, get_hairstyle_guide


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_FORMATS = {"JPEG": {"jpg", "jpeg"}, "PNG": {"png"}, "WEBP": {"webp"}}
ALLOWED_EXTENSIONS = {extension for extensions in ALLOWED_FORMATS.values() for extension in extensions}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES + 64 * 1024
CORS(app)

BODY_TYPES = {"Pear", "Apple", "Hourglass", "Rectangle", "Inverted Triangle"}
SKIN_TONES = {"Fair", "Medium", "Wheatish", "Deep"}
FACE_SHAPES = {"Round", "Oval", "Square", "Heart", "Diamond"}
OCCASIONS = {"Casual", "College", "Office", "Wedding", "Party"}
PREFERRED_STYLES = {"Western", "Traditional", "Indo-Western"}
HAIR_LENGTHS = {"Short", "Medium", "Long"}
HAIR_TEXTURES = {"Straight", "Wavy", "Curly", "Coily"}


@app.errorhandler(413)
def request_too_large(_error):
    app.logger.warning("Rejected an oversized request: %s", _error)
    return jsonify({"error": "Image exceeds the 10 MB size limit."}), 413


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "recommendation_model": model_status()})


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
        return jsonify({"error": "Image exceeds the 10 MB size limit."}), 413

    try:
        with Image.open(uploaded.stream) as image:
            image.verify()
        uploaded.stream.seek(0)
        with Image.open(uploaded.stream) as image:
            image_format = image.format
            width, height = image.size
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError):
        return jsonify({"error": "The file is not a valid or safe-to-process image."}), 400

    if image_format not in ALLOWED_FORMATS or extension not in ALLOWED_FORMATS[image_format]:
        return jsonify({"error": "File extension does not match the image format."}), 400
    if width * height > MAX_IMAGE_PIXELS:
        return jsonify({"error": "Image dimensions are too large to process safely."}), 400
    if width < 100 or height < 100:
        return jsonify({"error": "Image is too small. Use at least 100 x 100 pixels."}), 400

    stored_name = f"{uuid.uuid4().hex}.{extension}"
    stored_path = UPLOAD_DIR / stored_name
    uploaded.stream.seek(0)
    try:
        uploaded.save(stored_path)
    except OSError:
        app.logger.exception("Could not save uploaded image.")
        return jsonify({"error": "The image could not be saved on the server."}), 500

    try:
        processed = preprocess_image(stored_path)
        faces = detect_faces(processed)
        detected = {"face_shape": "Unknown", "skin_tone": "Unknown"}
        analysis_note = "No face detected. Select categories manually."
        if len(faces) == 1:
            detected.update(classify_skin_tone(processed, faces[0]))
            analysis_note = "Face shape requires manual selection."
        elif len(faces) > 1:
            analysis_note = "Multiple faces detected. Select categories manually."
    except (ValueError, RuntimeError, OSError, cv2.error) as error:
        stored_path.unlink(missing_ok=True)
        app.logger.warning("Image analysis failed: %s", error)
        return jsonify({"error": "Image uploaded but could not be analyzed. Select categories manually."}), 422

    return jsonify({
        "uploaded": True,
        "filename": stored_name,
        "width": width,
        "height": height,
        "size_bytes": size,
        "face_count": len(faces),
        "analysis_note": analysis_note,
        "detected": detected,
    })


@app.get("/api/uploads/<filename>")
def uploaded_photo(filename):
    return send_from_directory(UPLOAD_DIR, filename)


def _validate_profile(payload):
    if not isinstance(payload, dict):
        return None, "A JSON profile object is required."

    numeric_fields = {
        "height_inches": (48, 83),
        "weight_kg": (30, 130),
        "age": (14, 60),
    }
    for field, (minimum, maximum) in numeric_fields.items():
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, f"{field} must be a number."
        if not minimum <= value <= maximum:
            return None, f"{field} must be between {minimum} and {maximum}."

    choices = {
        "body_type": BODY_TYPES,
        "skin_tone": SKIN_TONES,
        "face_shape": FACE_SHAPES,
        "occasion": OCCASIONS,
        "preferred_style": PREFERRED_STYLES,
        "hair_length": HAIR_LENGTHS,
        "hair_texture": HAIR_TEXTURES,
    }
    for field, allowed in choices.items():
        value = payload.get(field)
        if not isinstance(value, str) or value not in allowed:
            return None, f"{field} must be one of: {', '.join(sorted(allowed))}."

    return payload, None


def _build_recommendations(profile):
    occasion = profile["occasion"]
    face_shape = profile["face_shape"]
    hair_length = profile["hair_length"]
    hair_texture = profile["hair_texture"]
    predictions = get_recommendations(profile)
    colors_to_wear = predictions["palette"].split("|")
    what_to_wear, what_to_avoid = get_body_type_guide(profile["body_type"])
    _, hairstyle_best, hairstyle_avoid = get_hairstyle_guide(face_shape)

    height_m = profile["height_inches"] * 0.0254
    bmi = profile["weight_kg"] / (height_m * height_m)
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif bmi < 25:
        bmi_category = "Normal"
    elif bmi < 30:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

    model_basis = "ML prototype"
    return {
        "recommendation_method": "synthetic_ml_prototype",
        "model_info": model_status(),
        "recommendations": {
            "outfit": {"recommendation": predictions["outfit"], "basis": model_basis},
            "color_palette": {"basis": model_basis},
            "hairstyle": {"recommendation": predictions["hairstyle"], "basis": model_basis},
            "earrings": {"recommendation": predictions["earrings"], "basis": model_basis},
            "necklace": {"recommendation": predictions["necklace"], "basis": model_basis},
        },
        "styling_guide": {
            "outfit_tip": f"Choose fabrics and fit that feel comfortable for your {occasion.lower()} plans.",
            "what_to_wear": what_to_wear,
            "what_to_avoid": what_to_avoid,
            "colors_to_wear": colors_to_wear,
            "colors_to_avoid": get_color_avoidance(profile["skin_tone"]),
            "color_tip": "Prototype palette output is based on skin-tone and style labels in generated examples; check colors in person.",
            "hairstyle_best": hairstyle_best,
            "hairstyle_avoid": hairstyle_avoid,
            "hairstyle_tip": f"Suggestions are adapted for {hair_length.lower()} {hair_texture.lower()} hair.",
            "jewelry": {
                "earrings": "Choose a size that feels comfortable and suits the occasion.",
                "necklace": "Coordinate the necklace length with your neckline.",
                "bangles": "Try a simple stack or a single statement bangle.",
                "ring": "Choose a minimal band or one statement ring.",
            },
            "accessories": predictions["accessories"].split("|"),
        },
        "user_stats": {
            "bmi": round(bmi, 1),
            "bmi_category": bmi_category,
            "height_inches": profile["height_inches"],
            "weight_kg": profile["weight_kg"],
        },
    }


@app.post("/api/recommend")
def recommend():
    profile, error = _validate_profile(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(_build_recommendations(profile))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )

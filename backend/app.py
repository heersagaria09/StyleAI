import os
import uuid
from pathlib import Path

import cv2
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError

from image_analysis import classify_skin_tone, detect_faces, preprocess_image


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
    return jsonify({"error": "Image exceeds the 10 MB size limit."}), 413


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


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
    style = profile["preferred_style"]
    body_type = profile["body_type"]
    skin_tone = profile["skin_tone"]
    face_shape = profile["face_shape"]
    hair_length = profile["hair_length"]
    hair_texture = profile["hair_texture"]

    occasion_outfits = {
        "Casual": "a relaxed top with straight-leg trousers",
        "College": "a comfortable layered outfit with practical footwear",
        "Office": "a tailored top with well-fitted trousers",
        "Wedding": "an occasion-ready outfit with refined accessories",
        "Party": "a statement outfit balanced with simple accessories",
    }
    style_descriptors = {
        "Western": "Western",
        "Traditional": "traditional",
        "Indo-Western": "Indo-Western",
    }
    outfit = (
        f"Try {style_descriptors[style]} styling for {occasion.lower()}: "
        f"{occasion_outfits[occasion]}."
    )

    body_guides = {
        "Pear": (["Structured tops", "A-line skirts", "Straight-leg trousers"], ["Unbalanced proportions"]),
        "Apple": (["Open layers", "V-neck tops", "Straight-leg trousers"], ["Restrictive waistbands"]),
        "Hourglass": (["Wrap styles", "Defined-waist outfits", "Balanced necklines"], ["Hiding every waist detail"]),
        "Rectangle": (["Layered outfits", "Belts and waist definition", "Textured separates"], ["Overly boxy head-to-toe looks"]),
        "Inverted Triangle": (["V-neck tops", "Flowing skirts", "Wide-leg trousers"], ["Adding excess shoulder volume"]),
    }
    what_to_wear, what_to_avoid = body_guides[body_type]

    palettes = {
        "Fair": (["Teal", "Coral", "Navy Blue"], ["Washed-out Beige"]),
        "Medium": (["Emerald Green", "Royal Blue", "Burgundy"], ["Muted Grey"]),
        "Wheatish": (["Terracotta", "Olive Green", "Teal"], ["Washed-out Beige"]),
        "Deep": (["Mustard", "Ivory", "Electric Blue"], ["Ash Grey"]),
    }
    colors_to_wear, colors_to_avoid = palettes[skin_tone]

    hairstyles = {
        "Oval": ("Layers, side-swept styles, or a sleek bob", ["Long layers", "Soft waves", "Side part"], []),
        "Round": ("Long layers or a side part to add visual length", ["Long layers", "Side part", "Volume at the crown"], ["Heavy blunt bangs"]),
        "Square": ("Soft waves or layered styles to soften angular lines", ["Soft waves", "Side-swept fringe", "Layered bob"], ["Very blunt jaw-length cuts"]),
        "Heart": ("Chin-length layers or side-swept fringe", ["Side-swept fringe", "Chin-length layers", "Soft waves"], ["Excess volume at the crown"]),
        "Diamond": ("Soft fringe or chin-length layers for balance", ["Soft fringe", "Chin-length layers", "Tucked-behind-ear styles"], ["Excess width at the cheekbones"]),
    }
    hairstyle, hairstyle_best, hairstyle_avoid = hairstyles[face_shape]
    hairstyle = f"{hair_length} {hair_texture.lower()} hair: {hairstyle}."

    earrings = {
        "Oval": "Hoops, studs, or drop earrings",
        "Round": "Long drop or angular earrings",
        "Square": "Rounded hoops or soft drop earrings",
        "Heart": "Teardrop or chandelier earrings",
        "Diamond": "Studs or curved drop earrings",
    }[face_shape]
    necklace = {
        "Oval": "Most necklace lengths work; choose a proportion that suits the neckline",
        "Round": "A longer pendant can create a lengthening line",
        "Square": "A rounded or curved necklace softens angular necklines",
        "Heart": "A short, curved necklace balances a wider neckline",
        "Diamond": "A delicate, curved necklace complements angular features",
    }[face_shape]

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

    return {
        "recommendation_method": "rule-based",
        "recommendations": {
            "outfit": {"recommendation": outfit, "basis": "Rule-based"},
            "color_palette": {"basis": "Rule-based"},
            "hairstyle": {"recommendation": hairstyle, "basis": "Rule-based"},
            "earrings": {"recommendation": earrings, "basis": "Rule-based"},
            "necklace": {"recommendation": necklace, "basis": "Rule-based"},
        },
        "styling_guide": {
            "outfit_tip": f"Choose fabrics and fit that feel comfortable for your {occasion.lower()} plans.",
            "what_to_wear": what_to_wear,
            "what_to_avoid": what_to_avoid,
            "colors_to_wear": colors_to_wear,
            "colors_to_avoid": colors_to_avoid,
            "color_tip": "Color suggestions are general styling ideas; lighting and personal preference can change how colors appear.",
            "hairstyle_best": hairstyle_best,
            "hairstyle_avoid": hairstyle_avoid,
            "hairstyle_tip": f"Suggestions are adapted for {hair_length.lower()} {hair_texture.lower()} hair.",
            "jewelry": {
                "earrings": "Choose a size that feels comfortable and suits the occasion.",
                "necklace": "Coordinate the necklace length with your neckline.",
                "bangles": "Try a simple stack or a single statement bangle.",
                "ring": "Choose a minimal band or one statement ring.",
            },
            "accessories": ["A coordinating bag", "Comfortable shoes", "One complementary accessory"],
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

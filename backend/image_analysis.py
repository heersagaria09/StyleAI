import cv2
import mediapipe as mp
import numpy as np


MAX_ANALYSIS_SIZE = 1024
FACE_OVAL_LANDMARKS = (
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
    379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93,
    234, 127, 162, 21, 54, 103, 67, 109,
)


def _horizontal_distance(landmarks, first, second):
    return abs(float(landmarks[first].x - landmarks[second].x))


def estimate_face_shape(landmarks):
    face_length = abs(landmarks[10].y - landmarks[152].y)
    cheek_width = _horizontal_distance(landmarks, 234, 454)
    forehead_width = _horizontal_distance(landmarks, 103, 332)
    jaw_width = _horizontal_distance(landmarks, 172, 397)
    if min(face_length, cheek_width, forehead_width, jaw_width) <= 0:
        return "Unknown", {}

    left_cheek = _horizontal_distance(landmarks, 1, 234)
    right_cheek = _horizontal_distance(landmarks, 1, 454)
    if min(left_cheek, right_cheek) <= 0:
        return "Unknown", {}
    cheek_balance = min(left_cheek, right_cheek) / max(left_cheek, right_cheek)
    if cheek_balance < 0.55:
        return "Unknown", {"cheek_balance": round(cheek_balance, 3)}

    length_to_width = face_length / cheek_width
    forehead_to_jaw = forehead_width / jaw_width
    jaw_to_cheek = jaw_width / cheek_width
    cheek_to_forehead = cheek_width / forehead_width

    if forehead_to_jaw >= 1.15 and jaw_to_cheek <= 0.85:
        shape = "Heart"
    elif (
        length_to_width >= 1.30
        and cheek_to_forehead >= 1.10
        and cheek_width / jaw_width >= 1.10
    ):
        shape = "Diamond"
    elif length_to_width < 1.25 and jaw_to_cheek >= 0.88:
        shape = "Square"
    elif length_to_width < 1.30 and jaw_to_cheek < 0.88:
        shape = "Round"
    else:
        shape = "Oval"

    return shape, {
        "face_length_to_cheek_width": round(length_to_width, 3),
        "forehead_to_jaw_width": round(forehead_to_jaw, 3),
        "jaw_to_cheek_width": round(jaw_to_cheek, 3),
        "cheek_balance": round(cheek_balance, 3),
    }


def analyze_face_landmarks(image):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=2,
        refine_landmarks=False,
        min_detection_confidence=0.5,
    ) as face_mesh:
        result = face_mesh.process(rgb_image)

    faces = result.multi_face_landmarks or []
    analysis = {
        "face_count": len(faces),
        "face_shape": "Unknown",
        "landmarks": [],
        "measurements": {},
    }
    if len(faces) != 1:
        return analysis

    landmarks = faces[0].landmark
    shape, measurements = estimate_face_shape(landmarks)
    analysis.update({
        "face_shape": shape,
        "landmarks": [
            {
                "x": round(float(landmarks[index].x), 6),
                "y": round(float(landmarks[index].y), 6),
            }
            for index in FACE_OVAL_LANDMARKS
        ],
        "measurements": measurements,
    })
    return analysis


def preprocess_image(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The image could not be decoded.")

    height, width = image.shape[:2]
    scale = min(1.0, MAX_ANALYSIS_SIZE / max(height, width))
    if scale < 1.0:
        image = cv2.resize(
            image,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    luminance, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    luminance = clahe.apply(luminance)
    normalized = cv2.merge((luminance, a, b))
    normalized = cv2.cvtColor(normalized, cv2.COLOR_LAB2BGR)

    return normalized


def detect_faces(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        raise RuntimeError("OpenCV face cascade could not be loaded.")

    detections = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    faces = []
    for x, y, width, height in sorted(detections, key=lambda item: item[2] * item[3], reverse=True):
        faces.append({
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
        })
    return faces


def classify_skin_tone(image, face):
    x, y, width, height = face["x"], face["y"], face["width"], face["height"]
    if width <= 0 or height <= 0:
        return {"skin_tone": "Unknown", "confidence": 0.0, "reason": "No valid face region."}

    roi_x1 = max(0, x + round(width * 0.20))
    roi_x2 = min(image.shape[1], x + round(width * 0.80))
    roi_y1 = max(0, y + round(height * 0.30))
    roi_y2 = min(image.shape[0], y + round(height * 0.82))
    roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
    if roi.size == 0:
        return {"skin_tone": "Unknown", "confidence": 0.0, "reason": "Face region is outside the image."}

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
    hsv_mask = cv2.inRange(hsv, (0, 15, 35), (35, 170, 255))
    ycrcb_mask = cv2.inRange(ycrcb, (0, 135, 85), (255, 180, 135))
    mask = cv2.bitwise_and(hsv_mask, ycrcb_mask)

    pixels = roi[mask > 0]
    if pixels.shape[0] < 40:
        return {"skin_tone": "Unknown", "confidence": 0.0, "reason": "Reliable skin pixels were not detected."}

    lab = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB)
    luminance = float(np.median(lab[:, 0, 0]))
    chroma_a = float(np.median(lab[:, 0, 1]))
    chroma_b = float(np.median(lab[:, 0, 2]))

    if luminance >= 205:
        skin_tone = "Fair"
    elif luminance >= 178:
        skin_tone = "Medium"
    elif luminance >= 150:
        skin_tone = "Wheatish"
    else:
        skin_tone = "Deep"

    coverage = pixels.shape[0] / roi.shape[0] / roi.shape[1]
    confidence = round(min(99.0, max(25.0, coverage * 100.0)), 1)
    return {
        "skin_tone": skin_tone,
        "confidence": confidence,
        "luminance": round(luminance, 1),
        "chroma_a": round(chroma_a, 1),
        "chroma_b": round(chroma_b, 1),
    }

import cv2
import numpy as np


MAX_ANALYSIS_SIZE = 1024


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

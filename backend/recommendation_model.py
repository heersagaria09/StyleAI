import csv
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from style_catalog import FEATURE_COLUMNS, TARGET_COLUMNS, TARGET_FEATURES


BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR / "data" / "style_training_data.csv"
MODEL_PATH = BACKEND_DIR / "models" / "deep_style_recommender.joblib"
MODEL_ALGORITHM = "scikit-learn MLPClassifier (48, 24)"


def _train_models(dataset):
    models = {}
    for target in TARGET_COLUMNS:
        features = TARGET_FEATURES[target]
        feature_rows = [[row[feature] for feature in features] for row in dataset]
        labels = [row[target] for row in dataset]
        model = make_pipeline(
            OneHotEncoder(handle_unknown="ignore"),
            MLPClassifier(
                hidden_layer_sizes=(48, 24),
                max_iter=100,
                early_stopping=True,
                n_iter_no_change=8,
                random_state=42,
                tol=0.005,
            ),
        )
        model.fit(feature_rows, labels)
        models[target] = model
    return models


@lru_cache(maxsize=1)
def _load_models():
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_mtime >= DATASET_PATH.stat().st_mtime:
        bundle = joblib.load(MODEL_PATH)
        if bundle.get("algorithm") == MODEL_ALGORITHM:
            return bundle["models"], bundle["training_rows"]

    with DATASET_PATH.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if any(column not in reader.fieldnames for column in FEATURE_COLUMNS + TARGET_COLUMNS):
            raise ValueError(f"Training dataset is missing required columns: {DATASET_PATH}")
        dataset = list(reader)
    if not dataset:
        raise ValueError(f"Training dataset is empty or missing required columns: {DATASET_PATH}")

    models = _train_models(dataset)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "algorithm": MODEL_ALGORITHM,
        "models": models,
        "training_rows": len(dataset),
    }, MODEL_PATH)
    return models, len(dataset)


def get_recommendations(profile):
    models, _ = _load_models()
    predictions = {
        target: str(models[target].predict([[profile[column] for column in TARGET_FEATURES[target]]])[0])
        for target in TARGET_COLUMNS
    }
    return predictions


def model_status():
    if not DATASET_PATH.exists():
        return {
            "available": False,
            "kind": "experimental_synthetic_neural_network",
            "error": f"Training dataset not found: {DATASET_PATH.name}",
        }

    try:
        _, training_rows = _load_models()
    except (OSError, ValueError, KeyError) as error:
        return {
            "available": False,
            "kind": "experimental_synthetic_neural_network",
            "error": str(error),
        }

    return {
        "available": True,
        "kind": "experimental_synthetic_neural_network",
        "algorithm": MODEL_ALGORITHM,
        "training_rows": training_rows,
        "warning": (
            "Experimental neural-network prototype trained on generated styling rules; "
            "not validated against real user preferences or outcomes."
        ),
    }

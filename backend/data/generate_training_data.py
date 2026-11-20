import csv
import itertools
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from style_catalog import (  # noqa: E402
    BODY_TYPES,
    FACE_SHAPES,
    HAIR_LENGTHS,
    HAIR_TEXTURES,
    OCCASIONS,
    PREFERRED_STYLES,
    SKIN_TONES,
    TARGET_COLUMNS,
    build_training_labels,
)


OUTPUT_PATH = Path(__file__).with_name("style_training_data.csv")
INPUT_COLUMNS = (
    "body_type",
    "skin_tone",
    "face_shape",
    "occasion",
    "preferred_style",
    "hair_length",
    "hair_texture",
)


def generate_dataset(output_path=OUTPUT_PATH):
    columns = INPUT_COLUMNS + TARGET_COLUMNS
    values = itertools.product(
        BODY_TYPES,
        SKIN_TONES,
        FACE_SHAPES,
        OCCASIONS,
        PREFERRED_STYLES,
        HAIR_LENGTHS,
        HAIR_TEXTURES,
    )
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        row_count = 0
        for combination in values:
            profile = dict(zip(INPUT_COLUMNS, combination))
            writer.writerow({**profile, **build_training_labels(profile)})
            row_count += 1
    return row_count


if __name__ == "__main__":
    print(f"Generated {generate_dataset()} synthetic rows at {OUTPUT_PATH}")

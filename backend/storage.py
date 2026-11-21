import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@lru_cache(maxsize=1)
def _client_for_uri(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def _collection():
    uri = os.environ.get("MONGO_URI")
    if not uri:
        return None
    client = _client_for_uri(uri)
    database_name = os.environ.get("MONGO_DB_NAME", "styleai")
    return client[database_name]["recommendation_history"]


def mongodb_status():
    uri = os.environ.get("MONGO_URI")
    if not uri:
        return {"configured": False, "status": "not_configured"}

    try:
        _client_for_uri(uri).admin.command("ping")
    except PyMongoError:
        return {"configured": True, "status": "unavailable"}
    return {"configured": True, "status": "connected"}


def save_recommendation(profile, result):
    fields = (
        "height_inches",
        "weight_kg",
        "age",
        "body_type",
        "skin_tone",
        "face_shape",
        "occasion",
        "preferred_style",
        "hair_length",
        "hair_texture",
    )
    document = {
        "created_at": datetime.now(timezone.utc),
        "profile": {field: profile[field] for field in fields},
        "result": result,
    }

    try:
        collection = _collection()
        if collection is None:
            return {
                "requested": True,
                "saved": False,
                "error": "MongoDB is not configured. Set MONGO_URI in the local .env file.",
            }
        record = collection.insert_one(document)
    except PyMongoError:
        return {
            "requested": True,
            "saved": False,
            "error": "MongoDB could not save this recommendation. Check the URI, network access, and database permissions.",
        }

    return {"requested": True, "saved": True, "record_id": str(record.inserted_id)}


def save_feedback(record_id, rating):
    try:
        collection = _collection()
        if collection is None:
            return {
                "saved": False,
                "error": "MongoDB is not configured. Set MONGO_URI in the local .env file.",
            }
        result = collection.update_one(
            {"_id": ObjectId(record_id)},
            {
                "$set": {
                    "feedback": {
                        "rating": rating,
                        "scale": 5,
                        "created_at": datetime.now(timezone.utc),
                    }
                }
            },
        )
    except PyMongoError:
        return {
            "saved": False,
            "error": "MongoDB could not save this feedback. Check the URI, network access, and database permissions.",
        }

    if result.matched_count == 0:
        return {"saved": False, "not_found": True, "error": "The saved recommendation was not found."}
    return {"saved": True}

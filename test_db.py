from backend.storage import mongodb_status


if __name__ == "__main__":
    status = mongodb_status()
    if status["status"] == "not_configured":
        raise SystemExit("MongoDB is not configured. Set MONGO_URI in the local .env file.")
    if status["status"] != "connected":
        raise SystemExit("MongoDB is unavailable. Check the Atlas URI, network access, and credentials.")
    print("MongoDB connected successfully.")

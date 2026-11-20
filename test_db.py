from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
client.admin.command('ping')
print('MongoDB connected successfully ✅')
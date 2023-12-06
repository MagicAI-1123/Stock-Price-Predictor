from pymongo import mongo_client, ASCENDING
from dotenv import load_dotenv
import os

load_dotenv()

client = mongo_client.MongoClient(os.getenv('DATABASE_URL'))
print('🚀🚀🚀 Connected to MongoDB...')

db = client[os.getenv('MONGO_INITDB_DATABASE')]

import os 
import time
import requests
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# mongodb connection
client = MongoClient(os.getenv('MONGO_URI'))
db = client['api_monitor']
health_checks = db['health_checks']
incidents = db['incidents']

APIS = {
    {"name": "jsonplaceholder_api",
      "url": "https://jsonplaceholder.typicode.com/posts/1"},
    {"name": "open_meteo_api", 
     "url": "https://api.open-meteo.com/v1/forecast?latitude=20&longitude=20&current_weather=true"},
}

# consecutive fails before incident 
num_failures = 3

def ping_service
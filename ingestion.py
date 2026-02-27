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

APIS = [
    {"name": "jsonplaceholder_api",
      "url": "https://jsonplaceholder.typicode.com/posts/1"},
    {"name": "open_meteo_api", 
     "url": "https://api.open-meteo.com/v1/forecast?latitude=20&longitude=20&current_weather=true"},
]

# consecutive fails before incident 
num_failures = 3

def fetch(apis):
    """fetch from api and return health check document"""
    try:
        response = requests.get(apis["url"], timeout=5)
        return {
            "service": apis["name"],
            "url": apis["url"],
            "status_code": response.status_code,
            "response_time_ms": round(response.elapsed.total_seconds() * 1000),
            "is_healthy": response.status_code == 200,
            "timestamp": datetime.now(timezone.utc),
            "error": None,
        }
    except requests.exceptions.RequestException as e:
        return {
            "service": apis["name"],
            "url": apis["url"],
            "status_code": None,
            "response_time_ms": None,
            "is_healthy": False,
            "timestamp": datetime.now(timezone.utc),
            "error": str(e),
        }


def check_for_incident(api):
    """check last n health checks and create/resolve incidents accordingly."""

    # finding most recent 3 documents in health checks collection from service field - matching api
    recent = list(
        health_checks.find({"service": api})
        .sort("timestamp", -1)
        .limit(num_failures)
    )

    if len(recent) < num_failures:
        return

    all_unhealthy = all(not check["is_healthy"] for check in recent)
    latest_healthy = recent[0]["is_healthy"]

    # if last 3 checks all failed, create an incident if not there
    if all_unhealthy:
        active_incident = incidents.find_one(
            {"service": api, "status": "active"}
        )
        if not active_incident:
            incident = {
                "service": api,
                "started_at": recent[-1]["timestamp"],  
                "resolved_at": None,
                "type": "down",
                "status": "active",
            }
            incidents.insert_one(incident)
            print(f" incident created: {api} is down")

    # If latest check is healthy and theres an active incident resolve it
    elif latest_healthy:
        result = incidents.update_one(
            {"service": api, "status": "active"},
            {
                "$set": {
                    "resolved_at": datetime.now(timezone.utc),
                    "status": "resolved",
                }
            },
        )
        if result.modified_count > 0:
            print(f"incident reslved: {api} is back")


def main():
    print('starting health monitor...')
    
    i = 0
    while True:
        print(f'check at: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}')


        for api in APIS:
            check = fetch(api)
            health_checks.insert_one(check)

            status = "good" if check["is_healthy"] else "down"
            ms = f"{check['response_time_ms']}ms" if check["response_time_ms"] else "N/A"
            print(f"  {api['name']}: {status} ({ms})")

            check_for_incident(api["name"])

        print()
        i += 1
        if i == 20:
            print('finished')
            break

        time.sleep(20)

if __name__ == '__main__':
    main()
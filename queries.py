import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("PY_MONGO_URI"))
db = client["api_monitor"]
health_checks = db["health_checks"]
incidents = db["incidents"]



# basic querying


# 1. Find all health checks for a specific service
def get_checks_by_service(service_name):
    results = health_checks.find({"service": service_name})
    for doc in results:
        print(doc)

    """
    SELECT * FROM health_checks WHERE service = service_name;
    """


# 2. Find all checks where is_healthy is false
def get_unhealthy_checks():
    results = health_checks.find({"is_healthy": False})
    for doc in results:
        print(doc)

    """
    SELECT * FROM health_checks where 'is_healthy' = false
    """

# 3. Find checks in a specific time range
def get_checks_in_range(start, end):
    results = health_checks.find({
        "timestamp": {
            # $gte = greater than or equal to.   $lte = less than or equal to ; $lt = < ; $gt = >
            "$gte": start,
            "$lte": end
        }
    })
    for doc in results:
        print(doc)

    """
    SELECT * FROM health_checks WHERE timestamp >= start AND timestamp < end 
    """

# 4. Count total checks per service
def count_checks_per_service():
    for service in ["jsonplaceholder_api", "open_meteo_api"]:
        count = health_checks.count_documents({"service": service})
        print(f"{service}: {count} checks")

    """
    SELECT service, COUNT(*) as checks FROM health_checks GROUP BY service
    """


# aggregation pipelines

# 5. Average response time per service (last hour)
def avg_response_time():
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    pipeline = [
        # $match - only keeps documents that fufill requirement
        {"$match": {"timestamp": {"$gte": one_hour_ago}}},
        # the attributes? idk need to have $ in front of them when grouping
        {"$group": {
            "_id": "$service",  # this is like primary key
            "avg_response_ms": {"$avg": "$response_time_ms"}
        }},
        {"$sort": {"avg_response_ms": -1}} # sorting descending order
    ]
    for doc in health_checks.aggregate(pipeline):
        print(f"{doc['_id']}: {round(doc['avg_response_ms'], 2)}ms avg")

    """
    SELECT service, AVG(response_time_ms) FROM health_checks WHERE timestamp >= NOW() - INTERVAL 1 HOUR GROUP BY service 
    ORDER BY AVG(response_time_ms) DESC 
    """
# 6. Uptime percentage per service
def uptime_percentage():
    pipeline = [
        {"$group": {
            "_id": "$service",
            "total": {"$sum": 1}, # adds one for every docuemnt
            "healthy": {
                "$sum": {"$cond": ["$is_healthy", 1, 0]} # if the document is healthy then add 1 else add 0
            }
        }},
        {"$project": { # calculates percentage 
            "service": "$_id",
            "uptime_pct": {
                "$round": [ # self explanatory
                    {"$multiply": [
                        {"$divide": ["$healthy", "$total"]},
                        100
                    ]},
                    2
                ]
            },
            "total_checks": "$total",
            "healthy_checks": "$healthy"
        }}
    ]
    for doc in health_checks.aggregate(pipeline):
        print(f"{doc['service']}: {doc['uptime_pct']}% uptime ({doc['healthy_checks']}/{doc['total_checks']})")
    """
    SELECT service,
           COUNT(*) AS total_checks,
           SUM(CASE WHEN is_healthy = true THEN 1 ELSE 0 END) AS healthy_checks,
           ROUND(SUM(CASE WHEN is_healthy = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS uptime_pct
    FROM health_checks
    GROUP BY service;
    """

# 7. Slowest response time per service
def slowest_response():
    pipeline = [
        {"$group": {
            "_id": "$service",
            "max_response_ms": {"$max": "$response_time_ms"},
        }},
        {"$sort": {"max_response_ms": -1}}
    ]
    for doc in health_checks.aggregate(pipeline):
        print(f"{doc['_id']}: {doc['max_response_ms']}ms slowest")

    """
    SELECT
        service,
        MAX(response_time_ms)
    FROM health_checks
    GROUP BY service
    ORDER BY max(response...) DESC
    """

# 8. Group checks by hour to see performance trends
def hourly_trends():
    pipeline = [
        {"$group": {
            "_id": {
                "service": "$service",
                "hour": {"$hour": "$timestamp"}
            },
            "avg_response_ms": {"$avg": "$response_time_ms"},
            "total_checks": {"$sum": 1},
            "failures": {
                "$sum": {"$cond": ["$is_healthy", 0, 1]}
            }
        }},
        {"$sort": {"_id.hour": 1}}
    ]
    for doc in health_checks.aggregate(pipeline):
        print(f"{doc['_id']['service']} @ hour {doc['_id']['hour']}: "
              f"avg {round(doc['avg_response_ms'], 2)}ms, "
              f"{doc['failures']} failures out of {doc['total_checks']} checks")

    """
    SELECT 
        service,
        EXTRACT(HOUR FROM timestamp) as hour,
        AVG(avg_response_ms),
        COUNT(*) as total_checks,
        SUM(CASE WHEN is_healthy = true THEN 0 ELSE 1 END) as failures
    FROM health_checks
    GROUP BY service, EXTRACT(HOUR from timestamp)
    ORDER BY hour ASC
    """

# 9. Find time windows where BOTH services were down
def simultaneous_downtime():
    pipeline = [
        {"$match": {"is_healthy": False}},
        {"$group": {
            "_id": {
                "minute": {
                    "$dateToString": {
                        "format": "%Y-%m-%d %H:%M",
                        "date": "$timestamp"
                    }
                }
            },
            "services_down": {"$addToSet": "$service"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gte": 2}}},
        {"$sort": {"_id.minute": -1}}
    ]
    results = list(health_checks.aggregate(pipeline))
    if results:
        for doc in results:
            print(f"{doc['_id']['minute']}: {doc['services_down']} both down")
    else:
        print("No simultaneous downtime found.")

    """
    SELECT DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i') AS minute,
           GROUP_CONCAT(DISTINCT service) AS services_down,
           COUNT(*) AS count
    FROM health_checks
    WHERE is_healthy = false
    GROUP BY DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i')
    HAVING COUNT(*) >= 2
    ORDER BY minute DESC;
    """

# incident queries

# 10. Find all active (unresolved) incidents
def active_incidents():
    results = incidents.find({"status": "active"})
    for doc in results:
        print(doc)

    """
    SELECT * FROM incidents WHERE status = 'active'
    """
# 11. Average incident duration for resolved incidents
def avg_incident_duration():
    pipeline = [
        {"$match": {"status": "resolved", "resolved_at": {"$ne": None}}},
        {"$project": {
            "service": 1,
            "duration_minutes": {
                "$divide": [
                    {"$subtract": ["$resolved_at", "$started_at"]},
                    60000  # milliseconds to minutes
                ]
            }
        }},
        {"$group": {
            "_id": "$service",
            "avg_duration_min": {"$avg": "$duration_minutes"}
        }}
    ]
    results = list(incidents.aggregate(pipeline))
    if results:
        for doc in results:
            print(f"{doc['_id']}: avg {round(doc['avg_duration_min'], 2)} min per incident")
    else:
        print("No resolved incidents found.")

    """
    SELECT service,
           AVG(TIMESTAMPDIFF(MINUTE, started_at, resolved_at)) AS avg_duration_min
    FROM incidents
    WHERE status = 'resolved' AND resolved_at IS NOT NULL
    GROUP BY service;
    """

# 12. Service with the most incidents
def most_incidents():
    pipeline = [
        {"$group": {
            "_id": "$service",
            "incident_count": {"$sum": 1}
        }},
        {"$sort": {"incident_count": -1}},
        {"$limit": 1}
    ]
    results = list(incidents.aggregate(pipeline))
    if results:
        print(f"{results[0]['_id']}: {results[0]['incident_count']} incidents")
    else:
        print("No incidents found.")

    """
    SELECT 
        service,
        COUNT(*) as incident_count
    FROM incidents
    GROUP BY service
    ORDER BY incident_count DESC
    LIMIT 1
    """
# indexing and performance

# 13. Create compound index on service + timestamp
def create_compound_index():
    health_checks.create_index(
        [("service", ASCENDING), ("timestamp", DESCENDING)],
        name="service_timestamp_idx"
    )
    print("Compound index created: service + timestamp")


# 14. Create TTL index to auto-delete checks older than 7 days
def create_ttl_index():
    health_checks.create_index(
        "timestamp",
        expireAfterSeconds=7 * 24 * 60 * 60,  # 7 days in seconds
        name="ttl_7days"
    )
    print("TTL index created: auto-delete after 7 days")


# 15. Run explain on a query to see performance
def explain_query():
    print("=== WITHOUT INDEX (if not created yet) or WITH INDEX ===")
    explanation = health_checks.find(
        {"service": "jsonplaceholder_api"}
    ).sort("timestamp", -1).limit(10).explain()

    plan = explanation.get("queryPlanner", {}).get("winningPlan", {})
    print(f"Winning plan: {plan.get('stage')}")
    print(f"Full explain: {explanation.get('executionStats', {})}")




if __name__ == "__main__":
    print("\n=== 1. Checks for jsonplaceholder_api ===")
    get_checks_by_service("jsonplaceholder_api")

    print("\n=== 2. Unhealthy checks ===")
    get_unhealthy_checks()

    print("\n=== 3. Checks in last hour ===")
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    now = datetime.now(timezone.utc)
    get_checks_in_range(one_hour_ago, now)

    print("\n=== 4. Count per service ===")
    count_checks_per_service()

    print("\n=== 5. Avg response time (last hour) ===")
    avg_response_time()

    print("\n=== 6. Uptime percentage ===")
    uptime_percentage()

    print("\n=== 7. Slowest response ===")
    slowest_response()

    print("\n=== 8. Hourly trends ===")
    hourly_trends()

    print("\n=== 9. Simultaneous downtime ===")
    simultaneous_downtime()

    print("\n=== 10. Active incidents ===")
    active_incidents()

    print("\n=== 11. Avg incident duration ===")
    avg_incident_duration()

    print("\n=== 12. Most incidents ===")
    most_incidents()

    print("\n=== 13. Create compound index ===")
    create_compound_index()

    print("\n=== 14. Create TTL index ===")
    create_ttl_index()

    print("\n=== 15. Explain query ===")
    explain_query()
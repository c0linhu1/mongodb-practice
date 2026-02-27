const { MongoClient } = require("mongodb");
require("dotenv").config({ path: "/Users/colin/Downloads/mongopractice/.env" });

const client = new MongoClient(process.env.JS_MONGO_URI);

async function run() {
  try {
    await client.connect();
    const db = client.db("api_monitor");
    const healthChecks = db.collection("health_checks");
    const incidents = db.collection("incidents");

    // basic queries

    // 1. Find all health checks for a specific service
    console.log("\n=== 1. Checks for jsonplaceholder_api ===");
    const checks = await healthChecks.find({ service: "jsonplaceholder_api" }).toArray();
    console.log(checks);

    // 2. Find all unhealthy checks
    console.log("\n=== 2. Unhealthy checks ===");
    const unhealthy = await healthChecks.find({ is_healthy: false }).toArray();
    console.log(unhealthy);

    // 3. Find checks in a time range (last hour)
    console.log("\n=== 3. Checks in last hour ===");
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    const rangeChecks = await healthChecks.find({
      timestamp: { $gte: oneHourAgo, $lte: new Date() }
    }).toArray();
    console.log(rangeChecks);

    // 4. Count total checks per service
    console.log("\n=== 4. Count per service ===");
    for (const svc of ["jsonplaceholder_api", "open_meteo_api"]) {
      const count = await healthChecks.countDocuments({ service: svc });
      console.log(`${svc}: ${count} checks`);
    }

    // aggregation pipelines


    // 5. Average response time per service (last hour)
    console.log("\n=== 5. Avg response time (last hour) ===");
    const avgResponse = await healthChecks.aggregate([
      { $match: { timestamp: { $gte: oneHourAgo } } },
      { $group: {
        _id: "$service",
        avg_response_ms: { $avg: "$response_time_ms" }
      }},
      { $sort: { avg_response_ms: -1 } }
    ]).toArray();
    avgResponse.forEach(doc => {
      console.log(`${doc._id}: ${doc.avg_response_ms.toFixed(2)}ms avg`);
    });

    // 6. Uptime percentage per service
    console.log("\n=== 6. Uptime percentage ===");
    const uptime = await healthChecks.aggregate([
      { $group: {
        _id: "$service",
        total: { $sum: 1 },
        healthy: { $sum: { $cond: ["$is_healthy", 1, 0] } }
      }},
      { $project: {
        service: "$_id",
        uptime_pct: {
          $round: [{ $multiply: [{ $divide: ["$healthy", "$total"] }, 100] }, 2]
        },
        total_checks: "$total",
        healthy_checks: "$healthy"
      }}
    ]).toArray();
    uptime.forEach(doc => {
      console.log(`${doc.service}: ${doc.uptime_pct}% uptime (${doc.healthy_checks}/${doc.total_checks})`);
    });

    // 7. Slowest response time per service
    console.log("\n=== 7. Slowest response ===");
    const slowest = await healthChecks.aggregate([
      { $group: {
        _id: "$service",
        max_response_ms: { $max: "$response_time_ms" }
      }},
      { $sort: { max_response_ms: -1 } }
    ]).toArray();
    slowest.forEach(doc => {
      console.log(`${doc._id}: ${doc.max_response_ms}ms slowest`);
    });

    // 8. Hourly trends
    console.log("\n=== 8. Hourly trends ===");
    const hourly = await healthChecks.aggregate([
      { $group: {
        _id: { service: "$service", hour: { $hour: "$timestamp" } },
        avg_response_ms: { $avg: "$response_time_ms" },
        total_checks: { $sum: 1 },
        failures: { $sum: { $cond: ["$is_healthy", 0, 1] } }
      }},
      { $sort: { "_id.hour": 1 } }
    ]).toArray();
    hourly.forEach(doc => {
      console.log(`${doc._id.service} @ hour ${doc._id.hour}: avg ${doc.avg_response_ms.toFixed(2)}ms, ${doc.failures} failures out of ${doc.total_checks} checks`);
    });

    // incident queries

    // 9. Find all active incidents
    console.log("\n=== 9. Active incidents ===");
    const active = await incidents.find({ status: "active" }).toArray();
    console.log(active.length ? active : "No active incidents.");

    // 10. Service with the most incidents
    console.log("\n=== 10. Most incidents ===");
    const most = await incidents.aggregate([
      { $group: { _id: "$service", incident_count: { $sum: 1 } } },
      { $sort: { incident_count: -1 } },
      { $limit: 1 }
    ]).toArray();
    if (most.length) {
      console.log(`${most[0]._id}: ${most[0].incident_count} incidents`);
    } else {
      console.log("No incidents found.");
    }

  } finally {
    await client.close();
  }
}

run().catch(console.error);
# API Health Monitoring System

MONGODB ATLAS PRACTICE - USING PYMONGO AND NODEJS TO QUERY DATABASE - speedrun complete

API health monitoring system using Python and MongoDB Atlas that tracks endpoint availability, detects service degradation through automated incident detection, and analyzes uptime metrics via aggregation pipelines. Trying to get full experience with querying and collection/document initialization in mongodb atlas.

Inspired by production monitoring tools like Datadog and PagerDuty.
Also messed with node.js

## Features

- **Automated Health Checks** — fetches form 2 apis on a 20 second interval, logging status codes, response times, and health status to MongoDB
- **Incident Detection** — Automatically creates incident records after 3 consecutive failures and resolves them upon service recovery
- **Analytical Queries** — 12 queries covering basic CRUD, aggregation pipelines, and incident analysis with SQL equivalents for reference
- **Indexing & Performance** — Compound indexes, TTL indexes for automated data retention, and explain plans for query optimization - probably irrelevant except ttl indexes 

## Tech Stack

- **Python** — PyMongo, Requests, python-dotenv
- **MongoDB Atlas** — Free tier cluster
- **APIs Monitored:**
  - [JSONPlaceholder](https://jsonplaceholder.typicode.com) — Fake REST API
  - [Open-Meteo](https://open-meteo.com) — Weather forecast API

## Database Schema

### `health_checks` Collection
```json
{
  "service": "jsonplaceholder_api",
  "url": "https://jsonplaceholder.typicode.com/posts/1",
  "status_code": 200,
  "response_time_ms": 143,
  "is_healthy": true,
  "timestamp": "2026-02-27T14:30:00Z",
  "error": null
}
```

### `incidents` Collection
```json
{
  "service": "open_meteo_api",
  "started_at": "2026-02-27T14:30:00Z",
  "resolved_at": "2026-02-27T14:45:00Z",
  "type": "down",
  "status": "resolved"
}
```

## Queries Covered

### Basic Queries
- Filter by service, health status, and time range
- Count documents per service

### Aggregation Pipelines
- Average response time per service
- Uptime percentage calculation
- Max response time per service
- Hourly performance trends
- Simultaneous downtime detection

### Incident Analysis
- Active incident lookup
- Average incident duration
- Most incident-prone service

### Indexing
- Compound index on `service` + `timestamp`
- TTL index for automatic 7-day data retention
- Query explain plans for performance analysis

## Key MongoDB Concepts Demonstrated

| MongoDB | SQL Equivalent |
|---------|---------------|
| `find()` | `SELECT ... WHERE` |
| `$match` | `WHERE` |
| `$group` | `GROUP BY` |
| `$project` | `SELECT` (reshape) |
| `$sort` | `ORDER BY` |
| `$limit` | `LIMIT` |
| `$cond` | `CASE WHEN` |
| `$addToSet` | `GROUP_CONCAT(DISTINCT)` |
| Compound Index | `CREATE INDEX ... (col1, col2)` |
| TTL Index | `Scheduled DELETE job` |

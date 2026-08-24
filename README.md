# Background Job Orchestrator (Inngest + FastAPI)

An asynchronous background job processing system built with Python, FastAPI, and Inngest. This project demonstrates non-blocking request handling, event-driven task processing, status polling, automatic retries with backoff, and scheduled cron jobs.

---

## 🏛️ Architectural Overview

This application separates **HTTP request ingestion** from **heavy work execution**:
- **Non-Blocking Ingestion (Fast 202 Accepted)**: When a user requests a report via `POST /reports`, the API immediately validates the payload, assigns a unique report ID, persists a `pending` status record in memory, and emits a `report/requested` event to Inngest. The API responds immediately with an **HTTP 202 Accepted** status code in under 1 second, keeping the request loop fast and responsive.
- **Asynchronous Execution Pattern**: The heavy work (e.g. 8-second simulation, building report content) is offloaded asynchronously to background workers managed by Inngest.
- **Status Polling**: Clients query `GET /reports/{id}` to poll the processing state until it transitions from `pending` to `done` (or `failed`).

---

## 🚀 Getting Started

### 1. Start the FastAPI Application
```bash
uvicorn main:app --reload
```
*App runs at:* `http://localhost:8000`

### 2. Start the Inngest Dev Server
```bash
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```
*Inngest Dashboard available at:* `http://localhost:8288`

---

## 📊 Summary of API Endpoints & Inngest Functions

### API Endpoints

| Method | Endpoint | Description | Expected Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health check | `200 OK` |
| `POST` | `/reports` | Request a background report generation | `202 Accepted`, `400 Bad Request` |
| `GET` | `/reports/{id}` | Poll the current state of a report | `200 OK`, `404 Not Found` |
| `GET/POST/PUT` | `/api/inngest` | Inngest function handler endpoint | `200 OK` |

### Inngest Functions

| Function Name | Trigger | Description | Retries |
| :--- | :--- | :--- | :--- |
| `say-hello` | Event: `test/hello` | Simple test function with a 5s sleep step | 4 (Default) |
| `make-report` | Event: `report/requested` | Generates report content after an 8s sleep step | 2 |
| `heartbeat` | Cron: `* * * * *` | Scheduled every minute to calculate and log report state counts | 4 (Default) |

---

## 🧪 Sample Curl Test Outputs

### 1. Submit Report (Fast 202 Accepted Response)
```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{"topic": "Quantum Computing"}'
```
**Output:**
```json
{
  "id": "75bef0fc-346b-416c-abe6-f9f506a1a51d",
  "status": "pending"
}
```

### 2. Poll Immediately (Pending Status)
```bash
curl http://localhost:8000/reports/75bef0fc-346b-416c-abe6-f9f506a1a51d
```
**Output:**
```json
{
  "id": "75bef0fc-346b-416c-abe6-f9f506a1a51d",
  "topic": "Quantum Computing",
  "status": "pending"
}
```

### 3. Poll After Completion (Done Status)
```bash
curl http://localhost:8000/reports/75bef0fc-346b-416c-abe6-f9f506a1a51d
```
**Output:**
```json
{
  "id": "75bef0fc-346b-416c-abe6-f9f506a1a51d",
  "topic": "Quantum Computing",
  "status": "done",
  "result": "Report content for Quantum Computing"
}
```

### 4. Input Validation (400 Bad Request)
```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{"topic": ""}'
```
**Output:**
```json
{
  "error": "Topic is required"
}
```

---

## 🔍 Analysis & Insights

1. **Rejecting Bad Input (400) vs. Retrying Runtime Failures**:
   - **Rejecting Bad Input at the Door (400 Bad Request)**: Invalid payloads (e.g. missing or empty topic) are client errors. Retrying an invalid request will never succeed and wastes system resources, queuing queues, and worker execution time. Thus, malformed input is caught synchronously at the API boundary and rejected immediately without enqueuing background events.
   - **Retrying Runtime Failures**: Transient system failures (network timeouts, database connection drops, external API limits) may succeed on subsequent attempts. Retrying these background steps with exponential backoff ensures resilience without impacting client response times.

2. **Cron Schedule Reference**:
   - **Daily at 08:00**: `0 8 * * *`
   - **Weekly on Sundays at 22:00**: `0 22 * * 0`

---

## 🖼️ Inngest Dashboard Screenshot Placeholder

![Inngest Dashboard Screenshot](./docs/inngest-dashboard.png)
*(Placeholder reference for attaching a screenshot of the Inngest dashboard showing completed runs, retries, and cron events)*

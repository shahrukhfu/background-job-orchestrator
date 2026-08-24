import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI()

inngest_client = inngest.Inngest(app_id="report-api")

reports = {}


async def on_make_report_failure(ctx: inngest.Context, step: inngest.Step):
    report_id = ctx.event.data.get("id")
    if report_id in reports:
        reports[report_id]["status"] = "failed"
        reports[report_id]["error"] = "The report oven is broken!"


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context, step: inngest.Step):
    await step.sleep("sleep-5s", "5s")
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    on_failure=on_make_report_failure,
)
async def make_report(ctx: inngest.Context, step: inngest.Step):
    await step.sleep("do-the-slow-work", "8s")

    def build_report():
        report_id = ctx.event.data.get("id")
        topic = ctx.event.data.get("topic")

        if topic == "fail":
            raise Exception("The report oven is broken!")

        report_content = f"Report content for {topic}"
        if report_id in reports:
            reports[report_id]["status"] = "done"
            reports[report_id]["result"] = report_content
        return report_content

    return await step.run("build-report", build_report)


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context, step: inngest.Step):
    def count_reports():
        pending = sum(
            1 for r in reports.values() if r.get("status") == "pending"
        )
        done = sum(1 for r in reports.values() if r.get("status") == "done")
        failed = sum(
            1 for r in reports.values() if r.get("status") == "failed"
        )
        summary = {
            "pending": pending,
            "done": done,
            "failed": failed,
            "total": len(reports),
        }
        logger.info(
            f"Heartbeat summary - Pending: {pending}, Done: {done}, Failed: {failed}, Total: {len(reports)}"
        )
        return summary

    return await step.run("count-reports", count_reports)


inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello, make_report, heartbeat],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def create_report(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Topic is required"},
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "Topic is required"},
        )

    topic = body.get("topic")
    if not topic or not isinstance(topic, str) or not topic.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Topic is required"},
        )

    report_id = str(uuid.uuid4())
    report_data = {
        "id": report_id,
        "topic": topic,
        "status": "pending",
    }
    reports[report_id] = report_data

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": topic},
        )
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"id": report_id, "status": "pending"},
    )


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    if report_id not in reports:
        return JSONResponse(
            status_code=404,
            content={"error": "Report not found"},
        )
    return reports[report_id]





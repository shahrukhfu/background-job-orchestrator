import uuid
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api
from pydantic import BaseModel

app = FastAPI()

inngest_client = inngest.Inngest(app_id="report-api")

reports = {}


class ReportRequest(BaseModel):
    topic: str


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
)
async def make_report(ctx: inngest.Context, step: inngest.Step):
    await step.sleep("do-the-slow-work", "8s")

    def build_report():
        report_id = ctx.event.data.get("id")
        topic = ctx.event.data.get("topic")
        report_content = f"Report content for {topic}"
        if report_id in reports:
            reports[report_id]["status"] = "done"
            reports[report_id]["result"] = report_content
        return report_content

    return await step.run("build-report", build_report)


inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello, make_report],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def create_report(body: ReportRequest):
    report_id = str(uuid.uuid4())
    report_data = {
        "id": report_id,
        "topic": body.topic,
        "status": "pending",
    }
    reports[report_id] = report_data

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": body.topic},
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



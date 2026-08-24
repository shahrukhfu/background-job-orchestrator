from fastapi import FastAPI
import inngest
import inngest.fast_api

app = FastAPI()

inngest_client = inngest.Inngest(app_id="report-api")


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context, step: inngest.Step):
    await step.sleep("sleep-5s", "5s")
    return "Hello from the background!"


inngest.fast_api.serve(
    app,
    inngest_client,
    [say_hello],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


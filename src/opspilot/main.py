from fastapi import FastAPI, HTTPException
from .config import settings
from .database import Database
from .schemas import RunRequest, RunResponse, ApprovalDecision, ApprovalResponse
from .service import OpsPilotService


def create_app(service: OpsPilotService | None = None) -> FastAPI:
    db = Database(settings.database_path)
    workflow = service or OpsPilotService(db, settings.openai_api_key, settings.openai_model)
    app = FastAPI(title=settings.app_name, version="0.1.0",
                  description="Human-approved AI operations workflow demonstration.")
    app.state.workflow = workflow

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "opspilot"}

    @app.post("/api/v1/runs", response_model=RunResponse, status_code=201)
    def create_run(request: RunRequest):
        try:
            return workflow.create_run(request.message)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Workflow planning failed: {exc}") from exc

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str):
        run = workflow.db.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @app.post("/api/v1/approvals/{approval_id}/approve", response_model=ApprovalResponse)
    def approve(approval_id: str, decision: ApprovalDecision):
        result = workflow.decide(approval_id, True, decision.note)
        if not result:
            raise HTTPException(status_code=404, detail="Approval not found")
        return result

    @app.post("/api/v1/approvals/{approval_id}/reject", response_model=ApprovalResponse)
    def reject(approval_id: str, decision: ApprovalDecision):
        result = workflow.decide(approval_id, False, decision.note)
        if not result:
            raise HTTPException(status_code=404, detail="Approval not found")
        return result

    return app


app = create_app()

from datetime import datetime
from typing import Any

from .database import Database
from .planner import DeterministicPlanner, OpenAIPlanner
from .schemas import ActionResult
from .tools import ToolRegistry


class OpsPilotService:
    def __init__(self, db: Database, api_key: str | None = None, model: str = "gpt-4.1-mini"):
        self.db = db
        self.tools = ToolRegistry()
        self.planner = OpenAIPlanner(api_key, model) if api_key else DeterministicPlanner()

    def create_run(self, message: str) -> dict[str, Any]:
        actions = self.planner.plan(message)
        plan = [item["tool"] for item in actions]
        results: list[dict[str, Any]] = []
        pending_tasks: list[dict[str, str]] = []
        for item in actions:
            tool = item.get("tool")
            args = item.get("arguments", {})
            try:
                if tool == "help":
                    results.append(ActionResult(
                        tool="help", status="completed",
                        output={
                            "available_tools": ["crm_lookup", "email_draft", "task_create"],
                            "message": "Ask to look up a customer, draft an email, or create a follow-up task.",
                        },
                    ).model_dump())
                elif tool in ("crm_lookup", "email_draft"):
                    validated = self.tools.validate_arguments(tool, args)
                    output = getattr(self.tools, tool)(**validated)
                    results.append(ActionResult(tool=tool, status="completed", output=output).model_dump())
                elif tool == "task_create":
                    validated = self.tools.validate_arguments(tool, args)
                    pending_tasks.append(validated)
                    results.append(ActionResult(
                        tool=tool, status="awaiting_approval",
                        output={"message": "Task creation requires explicit approval."},
                    ).model_dump())
                else:
                    raise ValueError(f"Unsupported tool: {tool}")
            except (ValueError, TypeError) as exc:
                results.append(ActionResult(
                    tool=str(tool), status="failed", output={"error": str(exc)}
                ).model_dump())

        status = "awaiting_approval" if pending_tasks else "completed"
        run_id = self.db.save_run(message, status, plan, results)
        task_index = 0
        for result in results:
            if result["tool"] == "task_create" and result["status"] == "awaiting_approval":
                result["approval_id"] = self.db.create_approval(
                    run_id, "task_create", pending_tasks[task_index]
                )
                task_index += 1
        self.db.update_run_results(run_id, results, status)
        run = self.db.get_run(run_id)
        return {
            "run_id": run_id, "status": status, "plan": plan, "results": results,
            "created_at": datetime.fromisoformat(run["created_at"]),
        }

    def decide(self, approval_id: str, approve: bool, note: str | None = None) -> dict[str, Any] | None:
        decision = self.db.decide_approval(approval_id, approve, note)
        if not decision:
            return None
        result: dict[str, Any] = {}
        if decision["status"] == "approved":
            payload = decision["payload"]
            result = self.db.create_task(payload["title"])
        elif decision["status"] == "rejected":
            result = {"message": "Task creation was rejected; no task was created."}

        if decision["status"] in ("approved", "rejected"):
            run = self.db.get_run(decision["run_id"])
            if run:
                for action in run["results"]:
                    if action.get("approval_id") == approval_id:
                        action["status"] = "completed" if approve else "rejected"
                        action["output"] = result
                        break
                still_pending = any(
                    action.get("status") == "awaiting_approval" for action in run["results"]
                )
                run_status = "awaiting_approval" if still_pending else "completed"
                self.db.update_run_results(decision["run_id"], run["results"], run_status)

        return {
            "approval_id": approval_id,
            "status": decision["status"],
            "result": result,
        }

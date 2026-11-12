from typing import Any


DEMO_CUSTOMERS = [
    {"customer_id": "cus_001", "name": "Amina Yusuf", "email": "amina@example.test", "company": "Northstar Studio", "status": "active"},
    {"customer_id": "cus_002", "name": "Daniel Okafor", "email": "daniel@example.test", "company": "Brightpath Labs", "status": "active"},
]


class ToolRegistry:
    """Explicit allow-list of application-owned tools; no arbitrary code execution."""

    def crm_lookup(self, query: str) -> dict[str, Any]:
        needle = query.lower()
        matches = [c for c in DEMO_CUSTOMERS if needle in c["name"].lower()
                   or needle in c["company"].lower() or needle in c["customer_id"].lower()]
        # A generic request can still demonstrate the seeded CRM safely.
        if not matches and any(term in needle for term in ("customer", "crm", "client", "account")):
            matches = DEMO_CUSTOMERS[:1]
        return {"matches": matches, "source": "local_demo_data", "count": len(matches)}

    def email_draft(self, request: str) -> dict[str, Any]:
        return {
            "subject": "Following up",
            "body": f"Hello,\n\nI wanted to follow up regarding: {request.strip()}\n\nBest regards",
            "status": "draft_only",
            "sent": False,
        }

    @staticmethod
    def validate_arguments(tool: str, arguments: dict[str, Any]) -> dict[str, str]:
        field = {"crm_lookup": "query", "email_draft": "request", "task_create": "title"}.get(tool)
        if not field:
            raise ValueError(f"Unsupported tool: {tool}")
        value = arguments.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            raise ValueError(f"{field} must be a non-empty string of at most 1000 characters")
        return {field: value.strip()}

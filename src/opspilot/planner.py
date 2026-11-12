import json
from typing import Any


class DeterministicPlanner:
    """Predictable planner used by default and in tests; never executes tools itself."""

    def plan(self, message: str) -> list[dict[str, Any]]:
        text = message.lower()
        actions: list[dict[str, Any]] = []
        if any(word in text for word in ("customer", "crm", "account", "client")):
            actions.append({"tool": "crm_lookup", "arguments": {"query": message}})
        if any(word in text for word in ("email", "reply", "message", "follow up")):
            actions.append({"tool": "email_draft", "arguments": {"request": message}})
        if any(word in text for word in ("task", "remind", "follow-up", "follow up", "create")):
            actions.append({"tool": "task_create", "arguments": {"title": message[:160]}})
        if not actions:
            actions.append({"tool": "help", "arguments": {}})
        return actions


class OpenAIPlanner:
    """Optional structured planner. Tool execution remains inside the application."""

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def plan(self, message: str) -> list[dict[str, Any]]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "Return JSON only: {\\"actions\\":[...]}. Allowed tools: crm_lookup "
                    "(arguments.query string), email_draft (arguments.request string), "
                    "task_create (arguments.title string). Use only these tools. Never claim "
                    "an email was sent. Task creation is approval-gated."
                )},
                {"role": "user", "content": message},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        actions = data.get("actions", [])
        allowed = {"crm_lookup", "email_draft", "task_create"}
        if not isinstance(actions, list) or len(actions) > 5:
            raise ValueError("Planner returned an invalid action list")
        for item in actions:
            if not isinstance(item, dict) or item.get("tool") not in allowed or not isinstance(item.get("arguments", {}), dict):
                raise ValueError("Planner returned an unsupported tool or invalid arguments")
        return actions

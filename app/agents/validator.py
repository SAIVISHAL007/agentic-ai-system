"""Tool input validation and repair for planned steps."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from app.core.logging import logger
from app.llm.groq_client import BaseLLMClient, get_llm_client
from app.tools.base import tool_registry, BaseTool
from app.schemas.request_response import ExecutionStep


class ToolInputValidator:
    """Validate and repair tool inputs before execution."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()

    def validate_and_repair(
        self,
        step: ExecutionStep,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        """Validate tool inputs and attempt LLM repair if needed."""
        tool_name = step.tool_name.lower()
        tool = tool_registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{step.tool_name}' not found in registry")

        input_data = dict(step.input_data or {})
        context = context or {}

        for attempt in range(max_attempts + 1):
            errors = self._collect_errors(tool, input_data)
            if not errors:
                return input_data

            logger.warning(
                "Tool input validation failed for %s (attempt %s/%s): %s",
                tool_name,
                attempt + 1,
                max_attempts + 1,
                "; ".join(errors),
            )

            if attempt >= max_attempts:
                break

            repaired = self._repair_with_llm(
                tool=tool,
                step=step,
                goal=goal,
                context=context,
                current_input=input_data,
                errors=errors,
            )
            if not isinstance(repaired, dict):
                break

            input_data = repaired

        raise ValueError(
            f"Unable to repair tool input for '{tool_name}'. Validation errors: {errors}"
        )

    def _collect_errors(self, tool: BaseTool, input_data: Dict[str, Any]) -> List[str]:
        """Collect missing field and schema validation errors."""
        errors: List[str] = []
        missing = [
            field
            for field in tool.required_fields
            if not self._has_value(input_data.get(field))
        ]
        if missing:
            errors.append(f"missing required fields: {missing}")

        try:
            tool.input_schema.model_validate(input_data)
        except ValidationError as exc:
            errors.append(f"schema validation error: {exc}")

        return errors

    def _repair_with_llm(
        self,
        tool: BaseTool,
        step: ExecutionStep,
        goal: str,
        context: Dict[str, Any],
        current_input: Dict[str, Any],
        errors: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Ask the LLM to regenerate valid tool inputs."""
        schema_fields = self._format_schema_fields(tool)
        required_fields = tool.required_fields

        system_message = (
            "You are a tool input validator. Generate only a JSON object for tool inputs. "
            "Do not include any extra keys or surrounding text."
        )

        user_prompt = (
            "Regenerate tool input so it matches the tool schema and required fields. "
            "Do not include empty strings; omit optional fields if unknown.\n\n"
            f"Tool: {tool.name}\n"
            f"Description: {tool.description}\n"
            f"Required fields: {required_fields}\n"
            f"Schema fields:\n{schema_fields}\n\n"
            f"Goal: {goal}\n"
            f"Context: {context}\n"
            f"Current input: {current_input}\n"
            f"Validation errors: {errors}\n\n"
            "Return JSON object only."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ]

        response = self.llm_client.call(messages, temperature=0.2)
        try:
            parsed = self.llm_client.parse_json(response.content)
        except Exception as exc:
            logger.warning("Failed to parse repaired tool input: %s", exc)
            return None

        if isinstance(parsed, dict):
            return parsed

        logger.warning("Repaired tool input was not a JSON object")
        return None

    def _format_schema_fields(self, tool: BaseTool) -> str:
        """Format schema fields for prompting."""
        schema = tool.input_schema
        if not hasattr(schema, "model_fields"):
            return "- (no schema fields)"

        lines: List[str] = []
        for field_name, field_info in schema.model_fields.items():
            required = field_name in tool.required_fields
            desc = field_info.description or ""
            field_type = self._format_type(field_info.annotation)
            required_label = "required" if required else "optional"
            lines.append(f"- {field_name} ({field_type}, {required_label}): {desc}")

        return "\n".join(lines)

    def _format_type(self, annotation: Any) -> str:
        """Format type annotation for prompt readability."""
        if annotation is None:
            return "unknown"
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        return str(annotation)

    def _has_value(self, value: Any) -> bool:
        """Return True when a value is non-empty and usable."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict)):
            return len(value) > 0
        return True

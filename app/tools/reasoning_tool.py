"""Reasoning-only tool for informational answers without external actions."""
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolOutput
from app.llm.groq_client import get_llm_client
from app.core.logging import logger


class ReasoningToolInput(BaseModel):
    """Input schema for reasoning tool."""
    question: str = Field(..., description="Question to answer")
    context: str = Field(
        default="",
        description="Additional context for answering (optional)"
    )


class ReasoningTool(BaseTool):
    """
    Reasoning-only fallback for static knowledge and explanations.

    Use this tool only when:
    - No external data is required
    - No real-world action is needed
    - A tool-based execution path is not applicable
    """

    def __init__(self):
        self.llm = get_llm_client()

    @property
    def name(self) -> str:
        return "reasoning"

    @property
    def description(self) -> str:
        return "Reasoning-only answers when no external tools are required"

    @property
    def input_schema(self) -> type[BaseModel]:
        return ReasoningToolInput

    def execute(self, **kwargs) -> ToolOutput:
        """Answer a question using the LLM."""
        try:
            input_data = ReasoningToolInput(**kwargs)

            logger.debug(f"Answering question: {input_data.question}")

            system_message = (
                "You are an agentic execution system. Provide a concise, accurate"
                " explanation without implying external actions or live data access."
            )

            user_prompt = f"Question: {input_data.question}"

            if input_data.context:
                user_prompt += f"\n\nAdditional Context: {input_data.context}"

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ]

            response = self.llm.call(messages, temperature=0.3)
            answer = response.content.strip()

            if answer:
                logger.info("Question answered successfully")
                return ToolOutput(
                    success=True,
                    result={
                        "answer": answer,
                        "question": input_data.question,
                        "note": "Reasoning-only step; no external tools used",
                    },
                )

            return ToolOutput(
                success=False,
                result=None,
                error="Failed to generate answer",
            )

        except Exception as e:
            error_msg = f"Reasoning failed: {str(e)}"
            logger.error(error_msg)
            return ToolOutput(success=False, result=None, error=error_msg)
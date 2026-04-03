"""Reasoning-only tool for informational answers without external actions."""
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolOutput
from app.llm.groq_client import get_llm_client
from app.core.config import settings
from app.core.logging import logger


from typing import Union

class ReasoningToolInput(BaseModel):
    """Input schema for reasoning tool."""
    question: str = Field(..., description="Question to answer")
    context: Union[str, dict, list] = Field(
        default="",
        description="Additional context for answering (can be string, dict, or list)"
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
                "You are an agentic execution system. Provide a concise, accurate answer based on the provided context. "
                "CRITICAL: If context contains actual data (numbers, values, metrics), extract and use them directly in your answer. "
                "Do NOT say 'the value stored at key X' or 'I would need to retrieve'. Instead, provide the actual value from context. "
                "Never output unresolved template variables, placeholders, or variable-style tokens such as $bitcoin_price or {variable}. "
                "If context is insufficient, say so explicitly instead of describing what you would need."
            )

            user_prompt = f"Question: {input_data.question}"

            if input_data.context:
                formatted_context = self._format_context(input_data.context)
                user_prompt += f"\n\n{formatted_context}"

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ]

            response = self.llm.call(
                messages,
                temperature=0.3,
                max_tokens=settings.LLM_REASONING_MAX_TOKENS,
            )
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
    
    def _format_context(self, context: Union[str, dict, list]) -> str:
        """Format context based on its type for clear LLM prompt.
        
        Args:
            context: Context data (string, dict, or list)
        
        Returns:
            Formatted context string
        """
        if isinstance(context, str):
            return f"Context: {context}"
        
        if isinstance(context, dict):
            # Format dictionary as structured data
            formatted_lines = ["Context (Structured Data):"]
            
            # Handle GitHub repository metadata specifically
            if "name" in context and "url" in context:
                formatted_lines.append("\nGitHub Repository:")
                if context.get("name"):
                    formatted_lines.append(f"  • Name: {context['name']}")
                if context.get("description"):
                    formatted_lines.append(f"  • Description: {context['description']}")
                if context.get("stars") is not None:
                    formatted_lines.append(f"  • Stars: {context['stars']:,}")
                if context.get("forks") is not None:
                    formatted_lines.append(f"  • Forks: {context['forks']:,}")
                if context.get("language"):
                    formatted_lines.append(f"  • Primary Language: {context['language']}")
                if context.get("url"):
                    formatted_lines.append(f"  • URL: {context['url']}")
                if context.get("topics") and len(context["topics"]) > 0:
                    formatted_lines.append(f"  • Topics: {', '.join(context['topics'][:5])}")
            else:
                # Generic dictionary formatting
                for key, value in context.items():
                    if value is not None:
                        formatted_lines.append(f"  • {key}: {value}")
            
            return "\n".join(formatted_lines)
        
        if isinstance(context, list):
            # Format list as numbered items
            formatted_lines = ["Context (List Data):"]
            for i, item in enumerate(context[:5], 1):  # Limit to first 5 items
                formatted_lines.append(f"  {i}. {item}")
            if len(context) > 5:
                formatted_lines.append(f"  ... and {len(context) - 5} more items")
            return "\n".join(formatted_lines)
        
        # Fallback
        return f"Context: {str(context)}"
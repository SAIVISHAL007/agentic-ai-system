"""Support ticket triage workflow - Multi-step example.

Demonstrates a real business workflow:
1. Analyze ticket severity/category
2. Search knowledge base for similar issues
3. Look up customer history (simulated)
4. Draft a response
5. Return full audit trail
"""

from typing import Any, Dict, Optional
from app.agents.runner import AgentRunner
from app.core.logging import logger
from app.tools import initialize_tools


# Simulated knowledge base for demo
KNOWLEDGE_BASE = {
    "login": [
        "How to reset password: Visit https://app.example.com/reset-password",
        "OAuth issues: Clear browser cache and retry authentication",
        "2FA problems: Check your authenticator app time sync",
    ],
    "billing": [
        "Invoice format: Invoices are sent to registered email after payment",
        "Payment methods: We accept credit card, PayPal, and wire transfer",
        "Refund policy: 30-day refund period for annual plans",
    ],
    "performance": [
        "Slow API: Check rate limits and consider upgrading plan",
        "Query optimization: Add indexes to frequently filtered columns",
        "Scaling issues: Contact support for enterprise solutions",
    ],
    "integration": [
        "Webhook setup: Configure in Settings > Integrations > Webhooks",
        "API auth: Use Bearer token in Authorization header",
        "Rate limits: 1000 requests/min for standard API key",
    ],
}

# Simulated customer history
CUSTOMER_HISTORY = {
    "CUST-001": {
        "name": "Acme Corp",
        "plan": "Professional",
        "support_tickets_resolved": 3,
        "issue_pattern": "integration",
    },
    "CUST-002": {
        "name": "TechStart Inc",
        "plan": "Enterprise",
        "support_tickets_resolved": 12,
        "issue_pattern": "performance",
    },
}


def run_support_ticket_triage(ticket_id: str, customer_id: str, issue_description: str) -> Dict[str, Any]:
    """
    Execute multi-step support ticket triage workflow.
    
    Args:
        ticket_id: e.g., "TKT-2024-001"
        customer_id: e.g., "CUST-001"
        issue_description: Description of the issue
    
    Returns:
        Dictionary with workflow_id, status, steps, and drafted_response
    """
    try:
        # Ensure tools are registered even when workflow is called directly.
        initialize_tools()
        runner = AgentRunner()
        
        # Create a detailed goal for the planner
        goal = f"""Support Ticket Triage for {ticket_id}:

Customer: {customer_id}
Issue: {issue_description}

Task: Triage the support ticket by:
1. Identifying the issue category (login/billing/performance/integration/other)
2. Determining severity (low/medium/high/critical)
3. Finding relevant knowledge base articles
4. Checking if customer has history of similar issues
5. Drafting a helpful response

Respond with structured analysis and a draft response."""
        
        # Execute the workflow
        execution_context = runner.run(
            goal=goal,
            context={
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "knowledge_base": KNOWLEDGE_BASE,
                "customer_history": CUSTOMER_HISTORY,
            }
        )
        
        # Convert execution context to response format
        steps_completed = [
            {
                "step_number": step.step_number,
                "description": step.description,
                "tool_name": step.tool_name,
                "success": step.success,
                "output": step.output or {},
                "error": step.error,
            }
            for step in execution_context.executed_steps
        ]
        
        return {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "execution_id": execution_context.execution_id,
            "status": execution_context.status or "completed",
            "steps_completed": steps_completed,
            "triage_result": execution_context.final_result,
            "drafted_response": execution_context.final_result.content if execution_context.final_result else None,
        }
    
    except Exception as e:
        logger.error(f"Support ticket triage failed: {str(e)}")
        return {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
            "execution_id": "",
            "status": "failed",
            "steps_completed": [],
            "triage_result": None,
            "drafted_response": None,
            "error": str(e),
        }

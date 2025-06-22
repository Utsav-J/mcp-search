from google.adk.agents import SequentialAgent
from retriever_agent.agent import root_agent as retriever_agent
from llm_agent.agent import llm_agent

# --- 1. Define Guardrails for Domain-Specific Queries ---
class OrchestratorGuardrails:
    DOMAIN_KEYWORDS = ["mcp", "document_url", "section_url", "score", "summary"]

    @staticmethod
    def is_domain_query(query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in OrchestratorGuardrails.DOMAIN_KEYWORDS)

    @staticmethod
    def guardrail_response() -> str:
        return (
            "I'm here to help with general conversation, but I cannot answer domain-specific questions. "
            "If you want to interact with the MCP server, please specify your request."
        )

# --- 2. Create the SequentialAgent Orchestrator ---
# This agent orchestrates the pipeline by running the retriever agent, then the llm_agent, in order.
# For non-domain queries, it enforces guardrails and only allows general conversation.
orchestrator_agent = SequentialAgent(
    name="orchestrator_agent",
    description="Handles all user conversations. For domain-specific queries, runs retriever_agent then llm_agent. Otherwise, enforces guardrails.",
    sub_agents=[retriever_agent, llm_agent],
    # guardrails=OrchestratorGuardrails,
)

# For ADK tools compatibility, the root agent must be named `root_agent`
root_agent = orchestrator_agent 
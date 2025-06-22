from google.adk.agents import LlmAgent

# This agent is designed to receive the output from the retriever agent and generate a RAG response.
llm_agent = LlmAgent(
    model="gemini-2.0-flash",  # You can change to your preferred model
    name="llm_agent",
    instruction=(
        "You are a RAG (Retrieval-Augmented Generation) agent. "
        "You receive all the information retrieved by the retriever agent, including details such as score, title, summary, document_url, section_url, and any other fields. "
        "Your task is to synthesize this information and formulate a comprehensive, well-structured answer to the user's query. "
        "Cite sources where appropriate and ensure the response is clear and helpful."
    ),
    tools=[],  # No tools; this agent only processes input from the retriever agent
) 
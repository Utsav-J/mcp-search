from google.adk.agents import LlmAgent

# This agent extracts currency_pair and date_range from the user query.
llm_agent = LlmAgent(
    model="gemini-2.0-flash",  # You can change to your preferred model
    name="llm_agent",
    instruction=(
        "You are an information extraction agent. "
        "Given a user query about foreign transactions, extract and return two parameters: "
        "1. currency_pair: a string representing the currency pair (e.g., 'USD/CAD'). "
        "2. date_range: a string representing the date range in the format 'YYYY/MM/DD-YYYY/MM/DD'. "
        "If the information is not explicit, infer the most likely values from the query context. "
        "Return only these two parameters and nothing else."
    ),
    tools=[],  # No tools; this agent only extracts parameters from the user query
) 

root_agent = llm_agent
#!/usr/bin/env python3
"""
Test script to verify the prompt template fix
"""

import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Mock tool for testing
@tool
def mock_tool(query: str) -> str:
    """A mock tool for testing"""
    return f"Mock result for: {query}"

# System prompt
SYSTEM_PROMPT = """You are a helpful AI assistant with access to specialized tools.

**CRITICAL: You MUST explain your reasoning process step by step.**

**When to use tools:**
- Use tools for tasks that require real-time data, external APIs, or specialized computations
- Use tools for file operations, database queries, web searches, or system interactions

**Reasoning Process:**
1. First, analyze the user's question and determine what information is needed
2. Check if you have the required information in your knowledge base
3. If not, identify which tools might help and explain why
4. Use the tool and explain what you found
5. Synthesize the information to provide a comprehensive answer

Be efficient and thoughtful: use tools when they add value, but respond directly when you can provide accurate information from your knowledge base."""

async def test_prompt_template():
    """Test the prompt template fix"""
    
    print("🧪 Testing Prompt Template Fix...")
    
    try:
        # Create the LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", convert_system_message_to_human=True)
        
        # Create tools
        tools = [mock_tool]
        
        # Create prompt template (FIXED VERSION)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + "\n\nYou MUST explain your reasoning step by step before using any tools."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        print("✅ Prompt template created successfully")
        
        # Create agent with tools
        agent = create_openai_tools_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)
        
        print("✅ Agent executor created successfully")
        
        # Test with a simple query
        test_query = "Use the mock tool to get information about testing"
        
        print(f"🔍 Testing with query: {test_query}")
        
        # Execute the agent
        result = await agent_executor.ainvoke({"input": test_query})
        
        print("✅ Agent execution completed successfully")
        print(f"📝 Output: {result['output']}")
        
        # Check for intermediate steps
        if 'intermediate_steps' in result:
            print(f"🔧 Found {len(result['intermediate_steps'])} intermediate steps")
            for i, step in enumerate(result['intermediate_steps']):
                print(f"   Step {i+1}: {step[0].tool} -> {str(step[1])[:50]}...")
        else:
            print("⚠️ No intermediate steps found")
        
        print("\n🎉 Prompt template fix test PASSED!")
        
    except Exception as e:
        print(f"❌ Test FAILED with error: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting Prompt Template Fix Test...")
    asyncio.run(test_prompt_template())
    print("✅ Test completed!") 
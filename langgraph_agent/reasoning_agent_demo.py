import plotly.graph_objects as go
import asyncio
import chainlit as cl
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage, SystemMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json
from typing import List, Dict, Any
import time

load_dotenv()

# Enhanced system prompt for reasoning
SYSTEM_PROMPT = """You are a helpful AI assistant with access to specialized tools through MCP (Model Context Protocol).

**CRITICAL: You MUST explain your reasoning process step by step.**

**When to use tools:**
- Use tools for tasks that require real-time data, external APIs, or specialized computations
- Use tools for file operations, database queries, web searches, or system interactions
- Use tools when you need to retrieve current information or perform actions you cannot do directly
- Use tools for domain-specific tasks that your available tools are designed for

**When to respond directly:**
- Answer general knowledge questions from your training data
- Provide explanations, definitions, or educational content
- Engage in conversation, creative writing, or brainstorming
- Perform simple calculations or reasoning that don't require external data
- Give advice or opinions based on your training

**Tool usage guidelines:**
- Always examine what tools are available to you first
- Use the most appropriate tool for the specific task
- Combine multiple tools if needed for complex workflows
- Explain your reasoning when choosing to use or not use tools
- If a tool fails, try alternative approaches or explain the limitation

**Reasoning Process:**
1. First, analyze the user's question and determine what information is needed
2. Check if you have the required information in your knowledge base
3. If not, identify which tools might help and explain why
4. Use the tool and explain what you found
5. Synthesize the information to provide a comprehensive answer

Be efficient and thoughtful: use tools when they add value, but respond directly when you can provide accurate information from your knowledge base."""

class ReasoningTracker:
    """Tracks reasoning steps and tool usage"""
    
    def __init__(self):
        self.reasoning_steps = []
        self.tool_results = []
        self.start_time = time.time()
    
    def add_step(self, step_type: str, content: str, **kwargs):
        """Add a reasoning step"""
        step = {
            "step_type": step_type,
            "content": content,
            "timestamp": time.time() - self.start_time,
            **kwargs
        }
        self.reasoning_steps.append(step)
        print(f"🧠 [{step_type.upper()}] {content}")
    
    def add_tool_result(self, tool_name: str, input_data: Any, result: Any):
        """Add a tool result"""
        tool_result = {
            "tool_name": tool_name,
            "input": input_data,
            "result": result,
            "timestamp": time.time() - self.start_time
        }
        self.tool_results.append(tool_result)
        print(f"🔧 [TOOL] {tool_name}: {str(result)[:100]}...")

class ReasoningAgent:
    """Agent that tracks and displays reasoning process"""
    
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.tracker = ReasoningTracker()
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message with full reasoning tracking"""
        self.tracker = ReasoningTracker()  # Reset for new message
        
        # Step 1: Initial analysis
        self.tracker.add_step("analysis", f"Analyzing user request: {user_message}")
        
        # Step 2: Determine if tools are needed
        needs_tools = await self._analyze_tool_need(user_message)
        
        if needs_tools:
            # Step 3: Execute with tools
            result = await self._execute_with_tools(user_message)
        else:
            # Step 3: Direct response
            result = await self._execute_direct_response(user_message)
        
        # Step 4: Final reasoning
        self.tracker.add_step("completion", "Response generation completed")
        
        return {
            "response": result,
            "reasoning_steps": self.tracker.reasoning_steps,
            "tool_results": self.tracker.tool_results
        }
    
    async def _analyze_tool_need(self, user_message: str) -> bool:
        """Analyze if tools are needed"""
        tool_keywords = [
            "search", "find", "get", "retrieve", "fetch", "query", "data",
            "transaction", "exchange", "foreign", "currency", "file", "document",
            "lookup", "check", "verify", "calculate", "compute"
        ]
        
        message_lower = user_message.lower()
        needs_tools = any(keyword in message_lower for keyword in tool_keywords)
        
        self.tracker.add_step(
            "tool_analysis", 
            f"Tool need analysis: {'Tools needed' if needs_tools else 'No tools needed'}"
        )
        
        return needs_tools
    
    async def _execute_with_tools(self, user_message: str) -> str:
        """Execute with tool usage"""
        self.tracker.add_step("tool_execution", "Starting tool-based execution")
        
        try:
            # Create prompt template for reasoning
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT + "\n\nYou MUST explain your reasoning step by step before using any tools."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create agent with tools
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, return_intermediate_steps=True)
            
            # List available tools
            tool_names = [tool.name for tool in self.tools]
            self.tracker.add_step("tool_selection", f"Available tools: {tool_names}")
            
            # Execute the agent
            result = await agent_executor.ainvoke({"input": user_message})
            
            # Track tool usage from intermediate steps
            if 'intermediate_steps' in result:
                for step in result['intermediate_steps']:
                    tool_name = step[0].tool
                    tool_input = step[0].tool_input
                    tool_output = step[1]
                    
                    self.tracker.add_tool_result(tool_name, tool_input, tool_output)
                    self.tracker.add_step(
                        "tool_used", 
                        f"Successfully used tool '{tool_name}'"
                    )
            
            return result["output"]
            
        except Exception as e:
            self.tracker.add_step("error", f"Tool execution failed: {str(e)}")
            return f"Error: {str(e)}"
    
    async def _execute_direct_response(self, user_message: str) -> str:
        """Execute direct response without tools"""
        self.tracker.add_step("direct_response", "Generating direct response without tools")
        
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message)
            ]
            
            response = await self.llm.ainvoke(messages)
            self.tracker.add_step("response_generation", "Direct response generated successfully")
            
            return response.content
            
        except Exception as e:
            self.tracker.add_step("error", f"Response generation failed: {str(e)}")
            return f"Error: {str(e)}"

# MCP Configuration
multi_mcp_config = {
    "mcp1": {
        "url": "http://localhost:8001/mcp",
        "transport": "streamable_http",
    },
    "mcp2": {
        "url": "http://localhost:8002/mcp",
        "transport": "streamable_http",
    },
}

# Global variables
multi_mcp_client = MultiServerMCPClient(multi_mcp_config)
model_client = ChatGoogleGenerativeAI(model="gemini-2.0-flash", convert_system_message_to_human=True)
reasoning_agent = None

async def display_reasoning_visualization(reasoning_steps: List[Dict], tool_results: List[Dict]):
    """Display reasoning process in a visually appealing way"""
    if not reasoning_steps:
        return
    
    # Create reasoning timeline
    reasoning_content = "🧠 **Agent Reasoning Timeline:**\n\n"
    
    for i, step in enumerate(reasoning_steps, 1):
        step_type = step.get("step_type", "unknown")
        content = step.get("content", "")
        timestamp = step.get("timestamp", 0)
        
        # Choose emoji based on step type
        emoji_map = {
            "analysis": "🔍",
            "tool_analysis": "🤔",
            "tool_execution": "⚙️",
            "tool_selection": "📋",
            "tool_used": "✅",
            "direct_response": "💭",
            "response_generation": "✨",
            "completion": "🎯",
            "error": "❌"
        }
        
        emoji = emoji_map.get(step_type, "📝")
        
        reasoning_content += f"**{emoji} Step {i} ({step_type.replace('_', ' ').title()}):**\n"
        reasoning_content += f"⏱️ Time: {timestamp:.2f}s\n"
        reasoning_content += f"📝 {content}\n\n"
    
    # Add tool results summary
    if tool_results:
        reasoning_content += "**🔧 Tool Execution Summary:**\n\n"
        for result in tool_results:
            tool_name = result.get("tool_name", "Unknown")
            result_content = str(result.get("result", ""))
            timestamp = result.get("timestamp", 0)
            
            reasoning_content += f"**Tool:** `{tool_name}`\n"
            reasoning_content += f"**Time:** {timestamp:.2f}s\n"
            reasoning_content += f"**Result:** {result_content[:200]}...\n\n"
    
    # Send reasoning visualization
    await cl.Message(
        content=reasoning_content,
        author="🧠 Reasoning Process"
    ).send()

@cl.on_chat_start
async def start():
    """Initialize the reasoning agent"""
    global reasoning_agent
    
    msg = cl.Message(content="🔧 Initializing Reasoning Agent...")
    await msg.send()
    
    try:
        # Load tools from MCP servers
        tools = await multi_mcp_client.get_tools()
        
        # Create reasoning agent
        reasoning_agent = ReasoningAgent(model_client, tools)
        
        msg.content = "✅ Reasoning Agent is ready! Ask me anything and I'll show you my thinking process."
        await msg.update()
        
    except Exception as e:
        msg.content = f"❌ Failed to initialize agent: {str(e)}"
        await msg.update()
        print(f"Initialization error: {e}")

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages with reasoning visualization"""
    global reasoning_agent
    
    if not reasoning_agent:
        await cl.Message(content="❌ Agent not initialized. Please refresh the page.").send()
        return
    
    # Show processing steps
    async with cl.Step(name="reasoning", type="run") as step:
        step.output = "🧠 Starting reasoning process..."
        
        try:
            # Process message with reasoning tracking
            result = await reasoning_agent.process_message(message.content)
            
            # Display reasoning visualization
            await display_reasoning_visualization(
                result["reasoning_steps"], 
                result["tool_results"]
            )
            
            step.output = "✅ Reasoning process completed!"
            
        except Exception as e:
            step.output = f"Error: {str(e)}"
            result = {"response": f"❌ Error: {str(e)}"}
            print(f"Processing error: {e}")
    
    # Show follow-up actions
    actions = [
        cl.Action(
            name="explain_reasoning",
            label="🧠 Explain Reasoning Further",
            payload={"action": "explain_reasoning"}
        ),
        cl.Action(
            name="show_tools",
            label="🔧 Show Available Tools",
            payload={"action": "show_tools"}
        ),
        cl.Action(
            name="visualize_data",
            label="📈 Visualize Data",
            payload={"action": "visualize"}
        )
    ]
    
    await cl.Message(
        content=result["response"], 
        actions=actions
    ).send()

@cl.action_callback("explain_reasoning")
async def handle_explain_reasoning(action):
    """Show detailed reasoning explanation"""
    await cl.Message(
        content="""🧠 **Detailed Reasoning Explanation:**

The agent follows a systematic reasoning process:

1. **Analysis Phase**: The agent first analyzes your question to understand what you're asking for
2. **Tool Assessment**: It determines whether tools are needed based on keywords and context
3. **Execution Phase**: 
   - If tools are needed: It selects appropriate tools and executes them
   - If no tools needed: It generates a direct response using its knowledge
4. **Synthesis**: It combines all information to provide a comprehensive answer

Each step is tracked with timestamps to show the reasoning flow and decision-making process.""",
        author="Reasoning Explanation"
    ).send()

@cl.action_callback("show_tools")
async def handle_show_tools(action):
    """Show available tools"""
    if reasoning_agent:
        tool_list = "\n".join([f"- **{tool.name}**: {tool.description}" for tool in reasoning_agent.tools])
        await cl.Message(
            content=f"🔧 **Available Tools:**\n\n{tool_list}",
            author="Available Tools"
        ).send()
    else:
        await cl.Message(content="❌ No tools available").send()

@cl.action_callback("visualize_data")
async def handle_visualize_data(action):
    """Handle data visualization"""
    await cl.Message(content="📈 Data visualization feature coming soon!").send()

if __name__ == "__main__":
    cl.run() 
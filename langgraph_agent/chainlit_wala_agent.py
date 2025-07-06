import plotly.graph_objects as go
import asyncio
import chainlit as cl
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import json
from ref import sample_response_for_get_transactions
from chainlit import Action
from typing import TypedDict, Annotated, Sequence, Union, Dict, Any, List
import operator

load_dotenv()

# Define the state structure for our agent
class AgentState(TypedDict):
    messages: Annotated[Sequence[Union[HumanMessage, AIMessage, ToolMessage, SystemMessage]], operator.add]
    reasoning_steps: Annotated[List[Dict[str, Any]], operator.add]  # Track reasoning steps
    current_step: str  # Track current step type
    tool_results: Annotated[List[Dict[str, Any]], operator.add]  # Track tool results

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
multi_mcp_client = MultiServerMCPClient(multi_mcp_config)

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

model_client = ChatGoogleGenerativeAI(model="gemini-2.0-flash", convert_system_message_to_human=True)

# Custom reasoning prompt template
REASONING_PROMPT = """You are an AI assistant that must explain your reasoning process clearly.

Available tools: {tools}

Current conversation:
{messages}

User's question: {input}

**REASONING PROCESS:**
1. First, let me understand what the user is asking for...
2. Based on my analysis, I need to...
3. I will use the following approach...

Please provide your reasoning step by step, then either:
- Use a tool if needed (explain why you chose it)
- Provide a direct answer if no tool is needed

Remember to explain your thinking process clearly at each step."""

# Store active connections per session
active_connections = {}

class ReasoningAgent:
    """Custom agent that tracks reasoning steps"""
    
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.reasoning_steps = []
        self.tool_results = []
    
    async def ainvoke(self, state):
        """Invoke the agent with reasoning tracking"""
        messages = state.get("messages", [])
        
        # Reset reasoning tracking for this invocation
        self.reasoning_steps = []
        self.tool_results = []
        
        # Add initial reasoning step
        self.add_reasoning_step("analysis", "Starting analysis of user request")
        
        # Check if we need to use tools
        user_message = messages[-1].content if messages else ""
        needs_tools = await self.analyze_tool_need(user_message)
        
        if needs_tools:
            # Use tools with reasoning
            result = await self.execute_with_tools(messages)
        else:
            # Direct response
            result = await self.execute_direct_response(messages)
        
        # Add final reasoning step
        self.add_reasoning_step("completion", "Response generation completed")
        
        # Return state with reasoning data
        return {
            "messages": result.get("messages", messages),
            "reasoning_steps": self.reasoning_steps,
            "tool_results": self.tool_results,
            "current_step": "completed"
        }
    
    def add_reasoning_step(self, step_type, content, **kwargs):
        """Add a reasoning step"""
        step = {
            "step_type": step_type,
            "content": content,
            "timestamp": asyncio.get_event_loop().time(),
            **kwargs
        }
        self.reasoning_steps.append(step)
    
    async def analyze_tool_need(self, user_message):
        """Analyze if tools are needed for the user's request"""
        # Simple heuristic: check for keywords that suggest tool usage
        tool_keywords = [
            "search", "find", "get", "retrieve", "fetch", "query", "data",
            "transaction", "exchange", "foreign", "currency", "file", "document"
        ]
        
        message_lower = user_message.lower()
        needs_tools = any(keyword in message_lower for keyword in tool_keywords)
        
        self.add_reasoning_step(
            "tool_analysis", 
            f"Analyzing tool need: {'Tools needed' if needs_tools else 'No tools needed'} for: {user_message}"
        )
        
        return needs_tools
    
    async def execute_with_tools(self, messages):
        """Execute with tool usage"""
        self.add_reasoning_step("tool_execution", "Executing tool-based response")
        
        try:
            # Create a tool calling chain
            from langchain.agents import AgentExecutor, create_openai_tools_agent
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            
            # Create prompt template for reasoning
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT + "\n\nYou MUST explain your reasoning step by step before using any tools."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create agent with tools
            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, return_intermediate_steps=True)
            
            # Execute with reasoning tracking
            self.add_reasoning_step("tool_selection", f"Available tools: {[tool.name for tool in self.tools]}")
            
            # Get the user's question
            user_message = messages[-1].content if messages else ""
            
            # Execute the agent
            result = await agent_executor.ainvoke({"input": user_message})
            
            # Track tool usage from the result
            if 'intermediate_steps' in result:
                for step in result['intermediate_steps']:
                    tool_name = step[0].tool
                    tool_input = step[0].tool_input
                    tool_output = step[1]
                    
                    self.tool_results.append({
                        "tool_name": tool_name,
                        "input": tool_input,
                        "result": tool_output,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    
                    self.add_reasoning_step(
                        "tool_used", 
                        f"Used tool '{tool_name}' with input: {tool_input}",
                        tool_name=tool_name
                    )
            
            # Create final messages
            final_messages = messages + [AIMessage(content=result["output"])]
            result = {"messages": final_messages}
            
            self.add_reasoning_step("tool_result", "Tool execution completed successfully")
            
        except Exception as e:
            self.add_reasoning_step("tool_error", f"Tool execution failed: {str(e)}")
            result = {"messages": messages + [AIMessage(content=f"Error: {str(e)}")]}
        
        return result
    
    async def execute_direct_response(self, messages):
        """Execute direct response without tools"""
        self.add_reasoning_step("direct_response", "Generating direct response without tools")
        
        # Generate response using the LLM
        try:
            response = await self.llm.ainvoke(messages)
            result = {"messages": messages + [response]}
            self.add_reasoning_step("response_generation", "Direct response generated successfully")
        except Exception as e:
            self.add_reasoning_step("response_error", f"Response generation failed: {str(e)}")
            result = {"messages": messages + [AIMessage(content=f"Error: {str(e)}")]}
        
        return result

def create_custom_agent(tools):
    """Create a custom agent with reasoning visualization"""
    return ReasoningAgent(model_client, tools)

def extract_tool_context(messages):
    """Extract context from ToolMessage for enhanced AI response"""
    # 1. Detect if ToolMessage is present
    tool_call_made = any(isinstance(item, ToolMessage) for item in messages)
    
    if not tool_call_made:
        return None, None
    
    # 2. Extract the ToolMessage (if any)
    tool_message = next((m for m in messages if isinstance(m, ToolMessage)), None)
    
    if not tool_message:
        return None, None
    
    try:
        # 3. Parse and extract what you need
        tool_data = json.loads(tool_message.content)
        
        # 4. Extract specific info (e.g., from RAG hits)
        extracted_chunks = []
        document_urls = []
        
        for chunk in tool_data.get("result", {}).get("hits", []):
            title = chunk["record"].get("title", "Unknown Document")
            context = chunk["record"].get("raw_context", "")
            url = chunk["record"].get("url", "")
            
            if context:
                extracted_chunks.append(f"📘 {title}\n{context}\n" + "*" * 20)
            
            if url and url not in document_urls:
                document_urls.append(url)
        
        # 5. Combine extracted chunks
        final_chunk_text = "\n\n".join(extracted_chunks) if extracted_chunks else None
        
        return final_chunk_text, document_urls
        
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"Error parsing tool message: {e}")
        return None, None

def enhance_message_with_context(messages, extracted_context, document_urls):
    """Add extracted context to the conversation for better AI response"""
    if not extracted_context:
        return messages
    
    # Find the last user message and enhance it with context
    enhanced_messages = messages.copy()
    
    # Add context information before the final AI response
    context_message = {
        "role": "system", 
        "content": f"""Based on the tool search results, here is the relevant context that should inform your response:

        EXTRACTED CONTEXT:
        {extracted_context}

        DOCUMENT SOURCES:
        {', '.join(document_urls) if document_urls else 'No URLs available'}

        Please use this context to provide a comprehensive and accurate response to the user's query. Reference the specific information from these sources when relevant."""
    }
    
    # Insert context message before the last AI message generation
    enhanced_messages.append(context_message)
    return enhanced_messages
    
def enhance_tool_context_json(messages):
    """Extract JSON from GetForeignExchangeTransactionData tool and create a system message to represent it as a table."""
    # Find the latest ToolMessage
    tool_message = next((m for m in messages if isinstance(m, ToolMessage)), None)
    if not tool_message:
        return None
    try:
        tool_data = json.loads(tool_message.content)
        # Heuristically check if this is from GetForeignExchangeTransactionData
        # (since tool name may not be present, check for known keys)
        result = tool_data.get("result")
        if not result:
            return None
        # If result is a list of dicts, or a dict with transactionId, treat as FX transaction data
        if (isinstance(result, dict) and "transactionId" in result) or (
            isinstance(result, list) and result and isinstance(result[0], dict) and "transactionId" in result[0]
        ):
            # Prepare a system message
            json_str = json.dumps(result, indent=2)
            system_message = {
                "role": "system",
                "content": (
                    "You have received the following Foreign Exchange Transaction Data from a tool call. "
                    "Represent this data as a table in your response. If there are nested fields, flatten them appropriately. "
                    "Here is the data (in JSON):\n\n"
                    f"{json_str}"
                ),
            }
            print(result)
            cl.user_session.set("current_message_context_json", result)
            return system_message
        return None
    except Exception as e:
        print(f"Error in enhance_tool_context_json: {e}")
        return None

async def display_reasoning_steps(reasoning_steps, tool_results):
    """Display reasoning steps in the UI"""
    if not reasoning_steps:
        return
    
    # Create a formatted display of reasoning steps
    reasoning_content = "🧠 **Agent Reasoning Process:**\n\n"
    
    for i, step in enumerate(reasoning_steps, 1):
        step_type = step.get("step_type", "unknown")
        content = step.get("content", "")
        
        if step_type == "reasoning":
            reasoning_content += f"**Step {i}: Analysis** 🤔\n{content}\n\n"
        elif step_type == "tool_result_analysis":
            reasoning_content += f"**Step {i}: Tool Result Analysis** 🔧\n{content}\n\n"
        elif step_type == "direct_response":
            reasoning_content += f"**Step {i}: Direct Response** 💭\n{content}\n\n"
        else:
            reasoning_content += f"**Step {i}: {step_type.title()}**\n{content}\n\n"
    
    # Display tool results if any
    if tool_results:
        reasoning_content += "**📊 Tool Results:**\n\n"
        for result in tool_results:
            tool_name = result.get("tool_name", "Unknown Tool")
            reasoning_content += f"**Tool:** {tool_name}\n"
            reasoning_content += f"**Result:** {result.get('result', 'No result')[:200]}...\n\n"
    
    # Send reasoning display
    await cl.Message(
        content=reasoning_content,
        author="Agent Reasoning"
    ).send()

def create_enhanced_prompt_with_reasoning(tools, user_message):
    """Create an enhanced prompt that encourages reasoning"""
    tools_info = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
    
    enhanced_prompt = f"""You are an AI assistant that must explain your reasoning process clearly.

Available tools:
{tools_info}

User's question: {user_message}

**REASONING PROCESS:**
1. First, let me understand what the user is asking for...
2. Based on my analysis, I need to...
3. I will use the following approach...

Please provide your reasoning step by step, then either:
- Use a tool if needed (explain why you chose it)
- Provide a direct answer if no tool is needed

Remember to explain your thinking process clearly at each step."""
    
    return enhanced_prompt

async def create_mcp_session():
    """Create and initialize Multi-MCP session with proper error handling"""
    try:
        # Load tools from all MCP servers
        tools = await multi_mcp_client.get_tools()
        agent = create_custom_agent(tools)
        return {
            'agent': agent,
            'multi_mcp_client': multi_mcp_client,
            'tools': tools,  # Store tools for reasoning display
        }
    except Exception as e:
        print(f"Error creating Multi-MCP session: {e}")
        raise

async def cleanup_connection(connection_info):
    """Safely cleanup MCP connection"""
    try:
        if 'client_session' in connection_info:
            await connection_info['client_session'].__aexit__(None, None, None)
        if 'http_client' in connection_info:
            await connection_info['http_client'].__aexit__(None, None, None)
        if 'close_func' in connection_info:
            await connection_info['close_func']()
    except Exception as e:
        print(f"Error during cleanup: {e}")

@cl.on_chat_start
async def start():
    """Initialize the MCP session and agent when chat starts"""
    # Show loading message
    msg = cl.Message(content="🔧 Initializing Vantage Chat Agent...")
    await msg.send()
    
    try:
        # Create MCP session
        connection_info = await create_mcp_session()
        
        # Store connection info in user session
        cl.user_session.set("connection_info", connection_info)
        cl.user_session.set("message_history", [])
        
        # Store in global dict for cleanup (using session id as key)
        session_id = cl.user_session.get("id")
        active_connections[session_id] = connection_info
        
        # Update message to show ready state
        msg.content = "✅ Vantage Chat Agent is ready! Ask me anything."
        await msg.update()
        
    except Exception as e:
        msg.content=f"❌ Failed to initialize agent: {str(e)}"
        await msg.update()
        print(f"Initialization error: {e}")

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages with reasoning visualization"""
    connection_info = cl.user_session.get("connection_info")
    
    if not connection_info or 'agent' not in connection_info:
        await cl.Message(content="❌ Agent not initialized. Please refresh the page.").send()
        return
    
    # Show typing indicator
    async with cl.Step(name="thinking", type="run") as step:
        step.output = "🧠 Analyzing your request and planning response..."
        try:
            # Initialize state for this interaction
            initial_state = {
                "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message.content)],
                "reasoning_steps": [],
                "current_step": "start",
                "tool_results": []
            }
            
            # Get tools for reasoning display
            tools = connection_info.get('tools', [])
            
            # Create enhanced prompt with reasoning instructions
            enhanced_prompt = create_enhanced_prompt_with_reasoning(tools, message.content)
            
            # Update system message with reasoning instructions
            initial_state["messages"][0] = SystemMessage(content=enhanced_prompt)
            
            # Run the agent with reasoning tracking
            agent = connection_info['agent']
            step.output = "🔍 Executing reasoning process..."
            
            # Invoke the agent and capture the full execution
            response = await agent.ainvoke(initial_state)
            
            # Extract reasoning steps and tool results
            reasoning_steps = response.get("reasoning_steps", [])
            tool_results = response.get("tool_results", [])
            final_messages = response.get("messages", [])
            
            # Display reasoning process
            await display_reasoning_steps(reasoning_steps, tool_results)
            
            # Get the final AI response
            ai_messages = [msg for msg in final_messages if isinstance(msg, AIMessage)]
            final_response = ai_messages[-1].content if ai_messages else "No response generated"
            
            # Update step output
            step.output = "✅ Response generated with full reasoning process!"
            
            # Store conversation history
            message_history = cl.user_session.get("message_history", [])
            message_history.append({"role": "user", "content": message.content})
            message_history.append({"role": "assistant", "content": final_response})
            cl.user_session.set("message_history", message_history)
            
            # Store reasoning data for potential follow-up
            cl.user_session.set("last_reasoning_steps", reasoning_steps)
            cl.user_session.set("last_tool_results", tool_results)
            
        except Exception as e:
            step.output = f"Error: {str(e)}"
            final_response = f"❌ Sorry, I encountered an error: {str(e)}"
            print(f"Message processing error: {e}")
    
    # Show follow-up questions and actions
    follow_ups = [
        "Explain your reasoning further",
        "What tools did you consider?",
        "Show me the raw tool results"
    ]
    actions = [
        Action(
            name="followup",
            label=q,
            payload={"question": q, "response": final_response}
        )
        for q in follow_ups
    ]
    actions.append(
        Action(
            name="visualize_data",
            label="📈 Visualize Data",
            payload={"action": "visualize"}
        )
    )
    actions.append(
        Action(
            name="show_reasoning_details",
            label="🧠 Show Detailed Reasoning",
            payload={"action": "reasoning_details"}
        )
    )
    
    await cl.Message(content=final_response, actions=actions).send()



@cl.action_callback("visualize_data")
async def handle_visualize_action(action: cl.Action):
    json_data = sample_response_for_get_transactions

    if not json_data:
        await cl.Message(content="⚠️ No data found to visualize.").send()
        return

    if isinstance(json_data, dict):
        json_data = [json_data]

    x_vals = []
    y_vals = []

    for row in json_data:
        date = row.get("valueDate")
        amount_str = row.get("buyCurrencyAmount")
        try:
            amount = float(amount_str) if isinstance(amount_str, str) else amount_str
            if date and amount is not None:
                x_vals.append(date)
                y_vals.append(amount)
        except Exception:
            continue

    if not x_vals or not y_vals:
        await cl.Message(content="❌ Could not extract valid data to plot.").send()
        return

    # ✅ Create Plotly figure
    fig = go.Figure(
        data=[
            go.Scatter(x=x_vals, y=y_vals, mode="lines+markers", name="Buy Amount")
        ],
        layout=go.Layout(
            title="Buy Currency Amount Over Time",
            xaxis_title="Value Date",
            yaxis_title="Buy Currency Amount",
        )
    )

    # ✅ Send it using Chainlit's Plotly element
    await cl.Message(
        content="📈 Here's the visualization of Buy Currency Amount over Value Date:",
        elements=[
            cl.Plotly(name="buy-amount-chart", figure=fig, display="inline", size="large")
        ]
    ).send()

# Handler for follow-up action
@cl.action_callback("followup")
async def handle_followup(action):
    question = action.payload.get("question", "")
    response = action.payload.get("response", "")
    
    # Create a follow-up message based on the question
    follow_up_content = f"**Follow-up Question:** {question}\n\n**Previous Response:** {response}\n\nPlease provide additional details or clarification."
    
    await cl.Message(content=follow_up_content, author="User Follow-up").send()

@cl.action_callback("show_reasoning_details")
async def handle_show_reasoning_details(action):
    """Show detailed reasoning information"""
    reasoning_steps = cl.user_session.get("last_reasoning_steps", [])
    tool_results = cl.user_session.get("last_tool_results", [])
    
    if not reasoning_steps:
        await cl.Message(content="⚠️ No reasoning details available for this conversation.").send()
        return
    
    # Create detailed reasoning display
    detailed_content = "🧠 **Detailed Reasoning Analysis:**\n\n"
    
    for i, step in enumerate(reasoning_steps, 1):
        step_type = step.get("step_type", "unknown")
        content = step.get("content", "")
        timestamp = step.get("timestamp", 0)
        
        detailed_content += f"**Step {i} ({step_type}):**\n"
        detailed_content += f"**Time:** {timestamp:.2f}s\n"
        detailed_content += f"**Content:** {content}\n"
        
        # Add tool-specific details
        if step_type == "tool_result_analysis":
            tool_name = step.get("tool_name", "Unknown")
            detailed_content += f"**Tool Used:** {tool_name}\n"
        
        detailed_content += "\n" + "-" * 50 + "\n\n"
    
    # Add tool results summary
    if tool_results:
        detailed_content += "**📊 Tool Execution Summary:**\n\n"
        for result in tool_results:
            tool_name = result.get("tool_name", "Unknown")
            result_content = result.get("result", "")
            timestamp = result.get("timestamp", 0)
            
            detailed_content += f"**Tool:** {tool_name}\n"
            detailed_content += f"**Execution Time:** {timestamp:.2f}s\n"
            detailed_content += f"**Result Length:** {len(str(result_content))} characters\n"
            detailed_content += f"**Result Preview:** {str(result_content)[:300]}...\n\n"
    
    await cl.Message(
        content=detailed_content,
        author="Detailed Reasoning"
    ).send()

@cl.on_chat_end
async def end():
    """Clean up when chat ends"""
    session_id = cl.user_session.get("id")
    
    if session_id in active_connections:
        connection_info = active_connections[session_id]
        await cleanup_connection(connection_info)
        del active_connections[session_id]

@cl.on_stop
async def stop():
    """Clean up all connections when server stops"""
    cleanup_tasks = []
    for connection_info in active_connections.values():
        cleanup_tasks.append(cleanup_connection(connection_info))
    
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    active_connections.clear()

if __name__ == "__main__":
    try:
        cl.run()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Ensure cleanup on exit
        if active_connections:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                for connection_info in active_connections.values():
                    asyncio.create_task(cleanup_connection(connection_info))
            else:
                asyncio.run(stop())
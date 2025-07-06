import plotly.graph_objects as go
import asyncio
import chainlit as cl
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
import json
from ref import sample_response_for_get_transactions
from chainlit import AskActionMessage, Action

load_dotenv()

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

# System prompt for guiding tool usage
SYSTEM_PROMPT = """You are a helpful AI assistant with access to specialized tools through MCP (Model Context Protocol).

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

**IMPORTANT: Always include a reasoning section in your response**
After providing your main answer, always include a "REASONING:" section that explains:
1. Tool Selection Reasoning: Show the chain of thought for selection of tool, based on the user's query
2. If you didn't use tools, explain why they weren't needed
3. What information sources you relied on for your response
4. Any assumptions or limitations in your reasoning

Be efficient and thoughtful: use tools when they add value, but respond directly when you can provide accurate information from your knowledge base."""

model_client = ChatGoogleGenerativeAI(model="gemini-2.0-flash", convert_system_message_to_human=True)


# Store active connections per session
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

        Please use this context to provide a comprehensive and accurate response to the user's query. Reference the specific information from these sources when relevant.
        
        Remember to include a "REASONING:" section explaining that you used a search tool to find relevant information and what sources you consulted."""
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
                    f"{json_str}\n\n"
                    "Remember to include a 'REASONING:' section explaining that you used the GetForeignExchangeTransactionData tool "
                    "to retrieve transaction data and why this tool was necessary for the user's request."
                ),
            }
            print(result)
            cl.user_session.set("current_message_context_json", result)
            return system_message
        return None
    except Exception as e:
        print(f"Error in enhance_tool_context_json: {e}")
        return None

def add_direct_response_reasoning(messages):
    """Add reasoning instructions for direct responses (no tools used)"""
    reasoning_message = {
        "role": "system",
        "content": (
            "You are providing a direct response without using any tools. "
            "Remember to include a 'REASONING:' section explaining why no tools were needed for this response. "
            "Mention that you're relying on your training data and general knowledge to answer this question."
        )
    }
    messages.append(reasoning_message)
    return messages

def extract_reasoning_from_response(response_content):
    """Extract the reasoning section from the AI response"""
    if not response_content:
        return None
    
    # Look for the reasoning section starting with REASONING:
    reasoning_marker = "REASONING:"
    if reasoning_marker in response_content:
        # Find the start of reasoning section
        start_idx = response_content.find(reasoning_marker)
        reasoning_text = response_content[start_idx:]
        return reasoning_text
    
    # Alternative markers if the main marker doesn't work
    alt_markers = ["Reasoning:", "🤔 Reasoning:", "🤔", "💭"]
    for marker in alt_markers:
        if marker in response_content:
            start_idx = response_content.find(marker)
            reasoning_text = response_content[start_idx:]
            return reasoning_text
    
    return None

# Store active connections per session
active_connections = {}

async def create_mcp_session():
    """Create and initialize Multi-MCP session with proper error handling"""
    try:
        # Load tools from all MCP servers
        tools = await multi_mcp_client.get_tools()
        agent = create_react_agent(model_client, tools, prompt=SYSTEM_PROMPT)
        return {
            'agent': agent,
            'multi_mcp_client': multi_mcp_client,
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
    """Handle incoming messages"""
    connection_info = cl.user_session.get("connection_info")
    
    if not connection_info or 'agent' not in connection_info:
        await cl.Message(content="❌ Agent not initialized. Please refresh the page.").send()
        return
    
    # Show typing indicator
    async with cl.Step(name="thinking", type="run") as step:
        step.output = "Processing your message..."
        try:
            # Get conversation history
            message_history = cl.user_session.get("message_history", [])
            if not message_history:
                message_history.append({"role": "system", "content": SYSTEM_PROMPT})
            message_history.append({"role": "user", "content": message.content})
            agent = connection_info['agent']
            response = await agent.ainvoke({"messages": message_history})
            full_messages = response.get("messages", []) if isinstance(response, dict) else []

            # --- MEMORY REFRESH & FOLLOW-UP LOGIC START ---
            first_tool_message = next((m for m in full_messages if isinstance(m, ToolMessage)), None)
            new_tool_call_signature = None
            tool_context_to_store = None
            if first_tool_message:
                tool_name = getattr(first_tool_message, 'name', None)
                try:
                    tool_content = json.loads(first_tool_message.content)
                except Exception:
                    tool_content = first_tool_message.content
                if isinstance(tool_content, dict):
                    params = tuple(sorted((k, str(v)) for k, v in tool_content.items() if k != 'result'))
                else:
                    params = tuple()
                new_tool_call_signature = (tool_name, params)
                tool_context_to_store = tool_content
            last_tool_call_signature = cl.user_session.get("last_tool_call", None)
            last_tool_context = cl.user_session.get("last_tool_context", None)
            context_reset = False
            is_followup = False
            if new_tool_call_signature and new_tool_call_signature != last_tool_call_signature:
                # New tool call detected, reset memory
                context_reset = True
                cl.user_session.set("last_tool_call", new_tool_call_signature)
                cl.user_session.set("last_tool_context", tool_context_to_store)
                message_history = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.content}]
                cl.user_session.set("message_history", message_history)
                await cl.Message(content="🔄 Context has been refreshed due to a new topic or data request.").send()
                response = await agent.ainvoke({"messages": message_history})
                full_messages = response.get("messages", []) if isinstance(response, dict) else []
            elif new_tool_call_signature:
                # Tool call, but same as last one, retain memory
                cl.user_session.set("last_tool_call", new_tool_call_signature)
                cl.user_session.set("last_tool_context", tool_context_to_store)
            elif not new_tool_call_signature and last_tool_context:
                # No new tool call, but we have previous tool context: this is a follow-up
                is_followup = True
            # --- MEMORY REFRESH & FOLLOW-UP LOGIC END ---

            if is_followup:
                # Reuse last tool context for follow-up
                await cl.Message(content="ℹ️ Reusing previous data context to answer your follow-up question.").send()
                # Add the last tool context as a system message
                enhanced_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                # Add the last tool context as a system message (format as JSON for clarity)
                json_str = json.dumps(last_tool_context, indent=2) if isinstance(last_tool_context, dict) else str(last_tool_context)
                enhanced_messages.append({
                    "role": "system",
                    "content": (
                        "You are answering a follow-up question. Here is the previous data context (in JSON):\n\n"
                        f"{json_str}\n\nUse this data to answer the user's question.\n\n"
                        "Remember to include a 'REASONING:' section explaining that you're reusing previous tool data "
                        "for this follow-up question and why no new tool call was needed."
                    )
                })
                enhanced_messages.append({"role": "user", "content": message.content})
                final_response = await agent.ainvoke({"messages": enhanced_messages})
                response = final_response
                # Add assistant response to history
                message_history.append({"role": "assistant", "content": str(response)})
                cl.user_session.set("message_history", message_history)
                
                # Extract and display reasoning in step output
                response_content = str(response['messages'][-1].content) if hasattr(response, 'get') and response.get('messages') else str(response)
                reasoning = extract_reasoning_from_response(response_content)
                if reasoning:
                    step.output = f"Response generated using previous context!\n\nREASONING:\n{reasoning}"
                else:
                    step.output = "Response generated using previous context!"
            elif not full_messages:
                # Direct response - add reasoning instructions
                enhanced_messages = add_direct_response_reasoning(message_history.copy())
                final_response = await agent.ainvoke({"messages": enhanced_messages})
                response = final_response
                message_history.append({"role": "assistant", "content": str(response)})
                cl.user_session.set("message_history", message_history)
                
                # Extract and display reasoning in step output
                response_content = str(response['messages'][-1].content) if hasattr(response, 'get') and response.get('messages') else str(response)
                reasoning = extract_reasoning_from_response(response_content)
                if reasoning:
                    step.output = f"Response generated with reasoning!\n\nREASONING:\n{reasoning}"
                else:
                    step.output = "Response generated with reasoning!"
            else:
                fx_tool_message = next((m for m in full_messages if isinstance(m, ToolMessage) and getattr(m, 'name', None) == 'GetForeignExchangeTransactionData'), None)
                if fx_tool_message:
                    system_message = enhance_tool_context_json(full_messages)
                    print("got json data\n\n\n\n")
                    enhanced_messages = message_history.copy()
                    if system_message:
                        enhanced_messages.append(system_message)
                    final_response = await agent.ainvoke({"messages": enhanced_messages})
                    response = final_response
                    message_history.append({"role": "assistant", "content": str(response)})
                    cl.user_session.set("message_history", message_history)
                    
                    # Extract and display reasoning in step output
                    response_content = str(response['messages'][-1].content) if hasattr(response, 'get') and response.get('messages') else str(response)
                    reasoning = extract_reasoning_from_response(response_content)
                    if reasoning:
                        step.output = f"Response generated with FX table context!\n\nREASONING:\n{reasoning}"
                    else:
                        step.output = "Response generated with FX table context!"
                else:
                    extracted_context, document_urls = extract_tool_context(full_messages)
                    if extracted_context:
                        context_msg = cl.Message(
                            content=f"**📚 Retrieved Context:**\n\n{extracted_context}",
                            author="System"
                        )
                        await context_msg.send()
                    enhanced_messages = enhance_message_with_context(
                        message_history, extracted_context, document_urls
                    )
                    if extracted_context:
                        final_response = await agent.ainvoke({"messages": enhanced_messages})
                        response = final_response
                    message_history.append({"role": "assistant", "content": str(response)})
                    cl.user_session.set("message_history", message_history)
                    
                    # Extract and display reasoning in step output
                    response_content = str(response['messages'][-1].content) if hasattr(response, 'get') and response.get('messages') else str(response)
                    reasoning = extract_reasoning_from_response(response_content)
                    if reasoning:
                        step.output = f"Response generated with enhanced context!\n\nREASONING:\n{reasoning}"
                    else:
                        step.output = "Response generated with enhanced context!"
        except Exception as e:
            step.output = f"Error: {str(e)}"
            response = f"❌ Sorry, I encountered an error: {str(e)}"
            print(f"Message processing error: {e}")
    # Show 3 dummy follow-up questions as buttons
    actions = []
    actions.append(
        Action(
            name="visualize_data",
            label="📈 Visualize Data",
            payload={"action": "visualize"}
        )
    )
    print(f"\n\n\n\n {cl.user_session.get('current_message_context_json', {})} ")
    await cl.Message(content=str(response['messages'][-1].content), actions=actions).send()
    # Store the last AI message content for later use

    # await AskActionMessage(
    #     content="Would you like to ask a follow-up question?",
    #     actions=actions
    # ).send()



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
    # last_ai_message = cl.user_session.get("last_ai_message")
    print(f"\n\n\n\n Previous AI message: {action.payload} ")
    # print(f"Previous AI message: {last_ai_message}")

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
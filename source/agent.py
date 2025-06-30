import asyncio
import json
import chainlit as cl
from litprinter import lit
from chat_config import chat_config
from utils import utils
import eggnog_web.prebuilt as prebuilt
from tachyon_langchain_client import TachyonLangchainClient
from langchain.core.messages import HumanMessage, ToolMessage
from langchain_mcp.mcp_client import MultiServerMCPClient
import dotenv
from urllib.parse import urlparse

dotenv.load_dotenv()

# Active connections
active_connections = {}

multi_mcp_config = {
    "mcp1": {
        "url": "http://localhost:8081/mcp",
        "tachyon search": "streamable_http",
    },
    "mcp2": {
        "url": "http://localhost:8082/mcp",
        "vantage services": "streamable_http",
    },
    "default_params": {
        "company_id": "STGCOMP2",
        "user_id": "SREEXOL",
        "company_name": "FXOL &TEST",
    },
}

multi_mcp_client = MultiServerMCPClient(multi_mcp_config)
model_client = TachyonLangchainClient(model_name="gemini-2.0-flash")
# The model_client was defined twice in the original snippets, keeping only one.


def extract_json_tool_context(messages):
    def identify_toolCall(messages):
        # 1. Detect if ToolMessage is present
        tool_call_made = any(isinstance(item, ToolMessage) for item in messages)
        if not tool_call_made:
            return None, None  # Modified to return None for both if no tool call
        # 2. Extract the ToolMessage (if any)
        tool_message = next(
            (m for m in messages if isinstance(m, ToolMessage)), None
        )
        if tool_message:
            return tool_message.name, tool_message
        return None, None

    """extract context from ToolMessage for enhanced AI response"""
    # 1. Detect if ToolMessage is present
    tool_call_made = any(isinstance(item, ToolMessage) for item in messages)
    if not tool_call_made:
        return None, None
    # 2. Extract the ToolMessage (if any)
    called_tool_name, tool_message = identify_toolCall(messages) # Reusing identify_toolCall
    
    lit.debug(f"tool_message.name: {tool_message.name}")
    if not tool_message:
        return None, None

    try:
        if called_tool_name == "SemanticSearch":
            print_(
                "EXTRACTING CONTEXT FROM SEMANTIC SEARCH RESULTS",
                level="debug",
                color_style="NEON",
            )
            final_chunk_text, document_urls = utils.extract_document_chunk_context(
                tool_message.content
            )
            return final_chunk_text, document_urls
        elif called_tool_name == "GetUSDVolumeTraded":
            print_(
                "EXTRACTING CONTEXT USD VOLUME", level="debug", color_style="NEON"
            )
            usd_volume_data = utils.extract_usd_volume_data_context(
                tool_message.content
            )
            return usd_volume_data, None
        else:
            json_context = utils.extract_general_json_context(
                tool_message.content
            )
            return json_context, None
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print_(f"Error parsing tool message: {e}")
        return None, None


def enhance_message_with_usd_doc_context(messages, extracted_context):
    if not extracted_context:
        return messages
    enhanced_messages = messages.copy()

    context_message = {
        "role": "system",
        "content": f"""Based on the tool call results, here is the relevant json data that you should align your response with.
Use the following data and create a well formatted table containing all the fields necessary
If the table contains more than 10 entries, provide a summarized form of a table
Before creating the complete table, also give insights based on the data and user's query.

Here is the data: {extracted_context}
""",
    }

    enhanced_messages.append(context_message)
    return enhanced_messages


def enhance_message_with_doc_context(messages, extracted_context, document_urls):
    """Add extracted context to the conversation for better AI response"""
    if not extracted_context:
        return messages

    # Find the last user message and enhance it with context
    enhanced_messages = messages.copy()

    # Add context information before the final AI response
    context_message = {
        "role": "system",
        "content": f"""Based on the tool search results, here is the relevant context that you should include in your response:
Please use this context to provide a comprehensive response as lengthy as possible.
Do not miss out on any details.
Do not perform any kind of summarization on the context.
Do not say things like "based on the given document" or anything synonymous that indicates presence of a context.
Do not mention about any reference documents or indicate the presence of reference documents in your response.

EXTRACTED CONTEXT:
{extracted_context}

DOCUMENT SOURCES:
{', '.join(document_urls) if document_urls else 'No URLs available'}
""",
    }
    # Insert context message before the last AI message generation
    enhanced_messages.append(context_message)
    return enhanced_messages


async def create_mcp_session():
    """create and initialize Multi-MCP session with proper error handling"""
    try:
        # load tools from all MCP servers
        tools = await multi_mcp_client.get_tools()
        agent = prebuilt.create_react_agent(
            model_client, tools, prompt=chat_config.SYSTEM_PROMPT
        )
        return {"agent": agent, "multi_mcp_client": multi_mcp_client}
    except Exception as e:
        print_(f"Error creating Multi-MCP session: {e}")
        raise


async def cleanup_connection(connection_info):
    """safely cleanup MCP connection"""
    try:
        if "client_session" in connection_info:
            await connection_info["client_session"].__aexit__(None, None, None)
        if "http_client" in connection_info:
            await connection_info["http_client"].__aexit__(None, None, None)
        if "close_func" in connection_info:
            await connection_info["close_func"]()
    except Exception as e:
        print_(f"Error during cleanup: {e}")


@cl.on_chat_start
async def start():
    """Initializing the MCP session and agent when chat starts"""
    # Show loading message
    msg = cl.Message(content="Initializing Vantage Chat Agent...")
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
        await msg.update(content=f"❌ Failed to initialize agent: {e}")
        print_(f"Initialization error: {e}")


@cl.on_message
async def main(message: cl.Message):
    """handle incoming messages"""
    connection_info = cl.user_session.get("connection_info")
    # clear the memory (This might be problematic if you intend to maintain conversation history)
    # cl.user_session.set("message_history", []) 
    # print_(f"MESSAGE HISTORY: {cl.user_session.get('message_history')}")

    markdown_links = []
    # Ensure message_history is initialized if not already present
    message_history = cl.user_session.get("message_history", [])
    message_history.append(HumanMessage(content=message.content)) # Append current user message
    cl.user_session.set("message_history", message_history)

    if not connection_info or "agent" not in connection_info:
        await cl.Message(
            content="❌ Agent not initialized. Please refresh the page."
        ).send()
        return

    # Show typing indicator
    async with cl.Step(name="Thinking", type="run") as step:
        # step.update() # No argument needed for update in this context
        agent = connection_info["agent"]
        
        full_message_response = await agent.ainvoke({"messages": message_history})
        full_message = full_message_response.get("messages", [])

        # If we don't have the full message chain, fallback to the response content
        if not full_message:
            # Add assistant response to history
            assistant_response_content = str(full_message_response) # Assuming full_message_response is the direct content if not a dict
            message_history.append({"role": "assistant", "content": assistant_response_content})
            cl.user_session.set("message_history", message_history)
            step.output = "Response generated!"
            response_to_send = assistant_response_content
        else:
            called_tool_name, tool_message_obj = extract_json_tool_context(full_message) # Getting both name and object
            
            extracted_context, document_urls = extract_json_tool_context(full_message) # Use the unified extraction function

            if document_urls:
                print_("FOUND DOCUMENTS!")
                # The original code had a conditional "if 'FOUND DOCUMENTS' in document_urls:" which seems like a typo.
                # Assuming document_urls is a list of URLs.
                for i, url in enumerate(document_urls, 1):
                    try:
                        print_("PARSING URL!")
                        parsed_url = urlparse(url)
                        domain = parsed_url.netloc
                        markdown_links.append(f"[{domain}]({url})")
                    except Exception:
                        # DEFAULT URL
                        markdown_links.append(f"[Source {i}]({url})")
                print_("ADDING TO THE TLIST")

                # Enhance messages with context for better final response
                enhanced_messages = enhance_message_with_doc_context(
                    message_history, extracted_context, document_urls
                )
                
                # Generate enhanced response with context
                if extracted_context:
                    final_response_obj = await agent.ainvoke({"messages": enhanced_messages})
                    response_content = final_response_obj.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print_(response_content)
                else:
                    response_content = full_message_response.get("choices", [{}])[0].get("message", {}).get("content", "")


                # Add assistant response to history
                message_history.append({"role": "assistant", "content": response_content})
                cl.user_session.set("message_history", message_history)
                step.name = "Response generated with enhanced context!"
                response_to_send = response_content

            else: # If no document_urls, check for USD context
                enhanced_messages = enhance_message_with_usd_doc_context(
                    message_history, extracted_context
                )
                if extracted_context:
                    final_response_obj = await agent.ainvoke({"messages": enhanced_messages})
                    response_content = final_response_obj.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print_(response_content)
                else:
                    response_content = full_message_response.get("choices", [{}])[0].get("message", {}).get("content", "")


                # Add assistant response to history
                message_history.append({"role": "assistant", "content": response_content})
                cl.user_session.set("message_history", message_history)
                step.name = "Response generated with enhanced context!"
                response_to_send = response_content


    except Exception as e:
        response_to_send = f"❌ Sorry, an error encountered an error: {e}"
        await cl.Message(content=f"❌ Processing error: {e}").send()
        print_(f"Error: {e}")

    # Prepare the final message content with references if available
    final_display_content = response_to_send
    if markdown_links:
        final_display_content += "\n**References**\n" + " | ".join(markdown_links)
    
    # Assuming utils.scan_response and passed_content are still relevant, otherwise remove or adapt
    # The 'passed_content' logic here is not fully clear from the snippets but assuming it's the initial user message.
    # If not, it needs to be explicitly passed or retrieved.
    # For now, let's assume `message.content` is the `passed_content` for the "For the devs" section.
    
    final_display_content = utils.scan_response(final_display_content)
    final_display_content += f"\n\n**For the devs**\n\n{message.content}" # Using message.content as passed_content

    await stream_response_to_user(final_display_content)
    # The line `await cl.Message(content=response_message_content).send()` might be redundant if `stream_response_to_user`
    # is intended to be the sole way to send the final message. Keep it if a complete message is needed after streaming.
    # await cl.Message(content=final_display_content).send()


async def stream_response_to_user(response):
    """Stream the response to the user character by character"""
    # Create an empty message
    ai_msg = cl.Message(content="", author="Vantage")
    await ai_msg.send()

    # Type out the content character by character
    for char in response:
        await ai_msg.stream_token(char)
    await ai_msg.update()


@cl.on_chat_end
async def end():
    """Clean up when chat ends"""
    session_id = cl.user_session.get("id")
    if session_id in active_connections:
        connection_info = active_connections[session_id]
        await cleanup_connection(connection_info)
        del active_connections[session_id]